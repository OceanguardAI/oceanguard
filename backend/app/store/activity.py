"""Process-local or PostgreSQL-backed GFW activity snapshots and source state."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from threading import RLock
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx

from app.models.schemas import ActivityAggregate, ActivityPage


def _error_category(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        code = error.response.status_code
        if code in (401, 403):
            return "unauthorized"
        if code == 429:
            return "quota_limited"
        return "provider_unavailable" if code >= 500 else "provider_error"
    if isinstance(error, httpx.TimeoutException):
        return "timeout"
    if isinstance(error, (ValueError, TypeError)):
        return "invalid_response"
    return "provider_error"


def _snapshot_id(items: list[ActivityAggregate]) -> UUID:
    fingerprint = sha256("|".join(sorted(item.id for item in items)).encode("utf-8")).hexdigest()
    return uuid5(NAMESPACE_URL, f"oceanguard-gfw:{fingerprint}")


class ActivityStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._items: list[ActivityAggregate] = []
        self._attempted_at: datetime | None = None
        self._succeeded_at: datetime | None = None
        self._error_category: str | None = None

    def replace(self, items: list[ActivityAggregate]) -> int:
        with self._lock:
            self._items = list(items)
            self._attempted_at = datetime.now(timezone.utc)
            self._succeeded_at = self._attempted_at
            self._error_category = None
            return len(self._items)

    def failure(self, error: Exception) -> None:
        with self._lock:
            self._attempted_at = datetime.now(timezone.utc)
            self._error_category = _error_category(error)

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "scope": "process_local",
                "last_attempt_at": self._attempted_at,
                "last_success_at": self._succeeded_at,
                "error_category": self._error_category,
                "aggregate_count": len(self._items),
            }

    def page(
        self,
        *,
        offset: int = 0,
        limit: int = 600,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> ActivityPage:
        with self._lock:
            items = self._items
            if bbox:
                west, south, east, north = bbox
                items = [a for a in items if west <= a.lon <= east and south <= a.lat <= north]
            total = len(items)
            state = "not_loaded" if self._succeeded_at is None else "available" if self._items else "empty"
            if self._succeeded_at and (
                self._error_category or datetime.now(timezone.utc) - self._succeeded_at > timedelta(hours=24)
            ):
                state = "stale"
            return ActivityPage(
                items=items[offset:offset + limit],
                total=total,
                offset=offset,
                limit=limit,
                data_state=state,
            )


class PostgresActivityStore:
    """Retain complete report snapshots and publish only the latest successful one."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self._dsn, row_factory=dict_row, connect_timeout=10)

    def replace(self, items: list[ActivityAggregate]) -> int:
        with self._connect() as conn:
            return self.write_snapshot(conn, items)

    def write_snapshot(self, conn, items: list[ActivityAggregate]) -> int:
        snapshot_id = _snapshot_id(items)
        start = items[0].report_start if items else None
        end = items[0].report_end if items else None
        if any(item.report_start != start or item.report_end != end for item in items):
            raise ValueError("Activity snapshot contains multiple report windows")
        if items:
            with conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO og_activity
                       (snapshot_id, id, dataset, detection_count, report_start,
                        report_end, provider_time, ingested_at, geom)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                               ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                       ON CONFLICT (snapshot_id, id) DO NOTHING""",
                    [
                        (snapshot_id, item.id, item.dataset, item.detection_count,
                         item.report_start, item.report_end, item.provider_time,
                         item.ingested_at, item.lon, item.lat)
                        for item in items
                    ],
                )
        conn.execute(
            """INSERT INTO og_source_state
               (source_key, last_attempt_at, last_success_at, error_category,
                snapshot_id, report_start, report_end)
               VALUES ('gfw_4wings', now(), now(), NULL, %s, %s, %s)
               ON CONFLICT (source_key) DO UPDATE SET
                 last_attempt_at = now(), last_success_at = now(),
                 error_category = NULL, snapshot_id = EXCLUDED.snapshot_id,
                 report_start = EXCLUDED.report_start,
                 report_end = EXCLUDED.report_end""",
            (snapshot_id, start, end),
        )
        return len(items)

    def failure(self, error: Exception) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO og_source_state (source_key, last_attempt_at, error_category)
                   VALUES ('gfw_4wings', now(), %s)
                   ON CONFLICT (source_key) DO UPDATE SET
                     last_attempt_at = now(), error_category = EXCLUDED.error_category""",
                (_error_category(error),),
            )

    def _state(self, conn):
        return conn.execute(
            "SELECT snapshot_id, last_attempt_at, last_success_at, error_category "
            "FROM og_source_state WHERE source_key = 'gfw_4wings'"
        ).fetchone()

    def status(self) -> dict[str, object]:
        with self._connect() as conn:
            state = self._state(conn)
            count = 0
            if state and state["snapshot_id"]:
                count = conn.execute(
                    "SELECT count(*) AS n FROM og_activity WHERE snapshot_id = %s",
                    (state["snapshot_id"],),
                ).fetchone()["n"]
        return {
            "scope": "database",
            "last_attempt_at": state["last_attempt_at"] if state else None,
            "last_success_at": state["last_success_at"] if state else None,
            "error_category": state["error_category"] if state else None,
            "aggregate_count": count,
        }

    def page(
        self,
        *,
        offset: int = 0,
        limit: int = 600,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> ActivityPage:
        with self._connect() as conn:
            state = self._state(conn)
            if not state or not state["snapshot_id"]:
                return ActivityPage(items=[], total=0, offset=offset, limit=limit, data_state="not_loaded")
            where = "snapshot_id = %s"
            params: list[object] = [state["snapshot_id"]]
            if bbox:
                where += " AND ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
                params.extend(bbox)
            total = conn.execute(
                "SELECT count(*) AS n FROM og_activity WHERE " + where, params
            ).fetchone()["n"]
            any_activity = conn.execute(
                "SELECT EXISTS(SELECT 1 FROM og_activity WHERE snapshot_id = %s) AS present",
                (state["snapshot_id"],),
            ).fetchone()["present"]
            rows = conn.execute(
                "SELECT id, dataset, ST_Y(geom) AS lat, ST_X(geom) AS lon, "
                "detection_count, report_start::text, report_end::text, provider_time, ingested_at "
                "FROM og_activity WHERE " + where + " ORDER BY detection_count DESC, id LIMIT %s OFFSET %s",
                [*params, limit, offset],
            ).fetchall()
        stale = bool(state["error_category"]) or (
            datetime.now(timezone.utc) - state["last_success_at"] > timedelta(hours=24)
        )
        return ActivityPage(
            items=[ActivityAggregate.model_validate(row) for row in rows],
            total=total, offset=offset, limit=limit,
            data_state="stale" if stale else "available" if any_activity else "empty",
        )


from app.core.config import settings

activity_store = PostgresActivityStore(settings.database_url) if settings.database_url else ActivityStore()
