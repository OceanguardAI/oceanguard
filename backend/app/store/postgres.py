"""PostGIS-backed risk events and append-only review history."""
from __future__ import annotations

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

import psycopg

from app.models.schemas import ReviewRecord, RiskEvent, RiskSummary
from app.store.repository import RiskEventRepository


class PostgresRiskEventRepository(RiskEventRepository):
    def __init__(self, dsn: str) -> None:
        super().__init__()
        self._dsn = dsn

    def _connect(self):
        return psycopg.connect(self._dsn, row_factory=dict_row, connect_timeout=10)

    def load(self) -> None:
        with self._connect() as conn:
            conn.execute("SELECT 1 FROM og_events LIMIT 1")
        self._mode = "external"

    def save(self) -> None:
        raise RuntimeError("PostgreSQL writes use transactional repository methods")

    def replace_all(self, events: list[RiskEvent], *, persist: bool = True) -> int:
        raise ValueError("Replacing durable case history is not supported")

    def upsert_many(self, events: list[RiskEvent], *, persist: bool = True) -> int:
        with self._connect() as conn:
            if events:
                with conn.cursor() as cur:
                    cur.executemany(
                        """INSERT INTO og_events
                           (id, source, risk_level, review_status, payload, geom)
                           VALUES (%s, %s, %s, %s, %s,
                                   ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                           ON CONFLICT (id) DO NOTHING""",
                        [
                            (e.id, e.source, e.risk_level, e.review_status,
                             Jsonb(e.model_dump()), e.lon, e.lat)
                            for e in events
                        ],
                    )
            count = conn.execute("SELECT count(*) AS n FROM og_events").fetchone()["n"]
        return count

    def all(
        self,
        source: str | None = None,
        level: str | None = None,
        review_status: str | None = None,
        near_mpa: bool | None = None,
    ) -> list[RiskEvent]:
        clauses: list[str] = []
        params: list[object] = []
        if source:
            clauses.append("source = %s")
            params.append(source)
        if level:
            clauses.append("risk_level = %s")
            params.append(level)
        if review_status:
            clauses.append("review_status = %s")
            params.append(review_status)
        if near_mpa is True:
            clauses.append("(payload->>'inside_mpa')::boolean OR (payload->>'near_mpa')::boolean")
        where = " WHERE " + " AND ".join(f"({c})" for c in clauses) if clauses else ""
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM og_events" + where + " ORDER BY created_at DESC", params).fetchall()
        return [RiskEvent.model_validate(row["payload"]) for row in rows]

    def get(self, event_id: str) -> RiskEvent | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM og_events WHERE id = %s", (event_id,)).fetchone()
        return RiskEvent.model_validate(row["payload"]) if row else None

    def update_review(self, event_id: str, status: str) -> RiskEvent | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM og_events WHERE id = %s FOR UPDATE", (event_id,)
            ).fetchone()
            if row is None:
                return None
            previous = RiskEvent.model_validate(row["payload"])
            updated = previous.model_copy(update={"review_status": status})
            conn.execute(
                "UPDATE og_events SET review_status = %s, payload = %s, updated_at = now() WHERE id = %s",
                (status, Jsonb(updated.model_dump()), event_id),
            )
            conn.execute(
                "INSERT INTO og_reviews (event_id, previous_status, review_status) VALUES (%s, %s, %s)",
                (event_id, previous.review_status, status),
            )
        return updated

    def summary(self) -> RiskSummary:
        """Override: base class reads self._events which is always empty in DB mode."""
        with self._connect() as conn:
            total = conn.execute("SELECT count(*) AS n FROM og_events").fetchone()["n"]
            source_rows = conn.execute(
                "SELECT source, count(*) AS n FROM og_events GROUP BY source"
            ).fetchall()
            level_rows = conn.execute(
                "SELECT risk_level, count(*) AS n FROM og_events GROUP BY risk_level"
            ).fetchall()
            status_rows = conn.execute(
                "SELECT review_status, count(*) AS n FROM og_events GROUP BY review_status"
            ).fetchall()
            inside_mpa = conn.execute(
                "SELECT count(*) AS n FROM og_events WHERE (payload->>'inside_mpa')::boolean"
            ).fetchone()["n"]
            near_mpa = conn.execute(
                "SELECT count(*) AS n FROM og_events WHERE (payload->>'near_mpa')::boolean"
            ).fetchone()["n"]
            top = conn.execute(
                "SELECT id, (payload->>'risk_score')::float AS score FROM og_events ORDER BY score DESC LIMIT 1"
            ).fetchone()
        return RiskSummary(
            total_events=total,
            source_counts={r["source"]: r["n"] for r in source_rows},
            risk_level_counts={r["risk_level"]: r["n"] for r in level_rows},
            review_status_counts={r["review_status"]: r["n"] for r in status_rows},
            inside_mpa_count=inside_mpa,
            near_mpa_count=near_mpa,
            highest_risk_event_id=top["id"] if top else None,
            highest_risk_score=top["score"] if top else None,
        )

    def review_history(self, event_id: str) -> list[ReviewRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, event_id, previous_status, review_status, actor_ref, reviewed_at "
                "FROM og_reviews WHERE event_id = %s ORDER BY id", (event_id,)
            ).fetchall()
        return [
            ReviewRecord(
                id=str(row["id"]), event_id=row["event_id"],
                previous_status=row["previous_status"], review_status=row["review_status"],
                actor_ref=row["actor_ref"], reviewed_at=row["reviewed_at"],
                storage_scope="database",
            )
            for row in rows
        ]
