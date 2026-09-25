"""PostgreSQL job queue with lease-token guarded completion."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from app.models.schemas import ActivityAggregate
from app.store.activity import PostgresActivityStore


def retry_delay_seconds(attempts: int) -> int:
    return min(60 * (2 ** max(0, attempts - 1)), 3600)


@dataclass(frozen=True)
class ClaimedJob:
    id: UUID
    job_type: str
    lease_token: UUID
    attempts: int


class PostgresJobQueue:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self):
        return psycopg.connect(self._dsn, row_factory=dict_row, connect_timeout=10)

    def enqueue_gfw(self, dedupe_key: str) -> UUID:
        if not dedupe_key or len(dedupe_key) > 200:
            raise ValueError("dedupe_key must be 1-200 characters")
        with self._connect() as conn:
            row = conn.execute(
                """INSERT INTO og_jobs (id, job_type, dedupe_key, status)
                   VALUES (%s, 'gfw_refresh', %s, 'queued')
                   ON CONFLICT (dedupe_key) DO UPDATE SET dedupe_key = EXCLUDED.dedupe_key
                   RETURNING id""",
                (uuid4(), dedupe_key),
            ).fetchone()
        return row["id"]

    def claim(self, lease_seconds: int = 1800) -> ClaimedJob | None:
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be positive")
        token = uuid4()
        with self._connect() as conn:
            conn.execute(
                """UPDATE og_jobs SET status = 'dead', lease_token = NULL,
                       lease_until = NULL, last_error_category = 'lease_expired',
                       updated_at = now(), finished_at = now()
                   WHERE status = 'running' AND lease_until <= now()
                     AND attempts >= max_attempts"""
            )
            row = conn.execute(
                """WITH candidate AS (
                       SELECT id FROM og_jobs
                       WHERE (status = 'queued' AND available_at <= now())
                          OR (status = 'running' AND lease_until <= now())
                       ORDER BY available_at, created_at
                       LIMIT 1 FOR UPDATE SKIP LOCKED
                   )
                   UPDATE og_jobs AS job SET
                       status = 'running', attempts = attempts + 1,
                       lease_token = %s,
                       lease_until = now() + (%s * interval '1 second'),
                       updated_at = now()
                   FROM candidate WHERE job.id = candidate.id
                   RETURNING job.id, job.job_type, job.attempts""",
                (token, lease_seconds),
            ).fetchone()
        if row is None:
            return None
        return ClaimedJob(row["id"], row["job_type"], token, row["attempts"])

    def complete_gfw(
        self, job: ClaimedJob, activity: PostgresActivityStore,
        rows: list[ActivityAggregate],
    ) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """UPDATE og_jobs SET status = 'succeeded', lease_until = NULL,
                       lease_token = NULL, last_error_category = NULL,
                       updated_at = now(), finished_at = now()
                   WHERE id = %s AND status = 'running' AND lease_token = %s
                     AND lease_until > now() RETURNING id""",
                (job.id, job.lease_token),
            ).fetchone()
            if row is None:
                return False
            activity.write_snapshot(conn, rows)
        return row is not None

    def fail(self, job: ClaimedJob, category: str) -> bool:
        if not category or len(category) > 80:
            raise ValueError("error category must be 1-80 characters")
        delay = retry_delay_seconds(job.attempts)
        with self._connect() as conn:
            row = conn.execute(
                """UPDATE og_jobs SET
                       status = CASE WHEN attempts >= max_attempts THEN 'dead' ELSE 'queued' END,
                       available_at = now() + (%s * interval '1 second'),
                       lease_until = NULL, lease_token = NULL,
                       last_error_category = %s, updated_at = now(),
                       finished_at = CASE WHEN attempts >= max_attempts THEN now() ELSE NULL END
                   WHERE id = %s AND status = 'running' AND lease_token = %s
                     AND lease_until > now() RETURNING id""",
                (delay, category, job.id, job.lease_token),
            ).fetchone()
            if row is not None:
                conn.execute(
                    """INSERT INTO og_source_state (source_key, last_attempt_at, error_category)
                       VALUES ('gfw_4wings', now(), %s)
                       ON CONFLICT (source_key) DO UPDATE SET
                         last_attempt_at = now(), error_category = EXCLUDED.error_category""",
                    (category,),
                )
        return row is not None

    def status(self, job_id: UUID) -> dict[str, object] | None:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT id, job_type, status, attempts, max_attempts, available_at,
                          lease_until, last_error_category, created_at, updated_at, finished_at
                   FROM og_jobs WHERE id = %s""",
                (job_id,),
            ).fetchone()
        return dict(row) if row else None


def daily_gfw_key(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return f"gfw-refresh:{current.astimezone(timezone.utc).date().isoformat()}"
