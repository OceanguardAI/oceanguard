"""Apply versioned PostgreSQL migrations before enabling DATABASE_URL on the API."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from app.core.config import settings

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def apply_migrations(dsn: str) -> list[str]:
    import psycopg

    applied: list[str] = []
    with psycopg.connect(dsn, connect_timeout=10) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS og_schema_migrations ("
            "version text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        conn.execute("SELECT pg_advisory_xact_lock(72490813)")
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            sql = path.read_text(encoding="utf-8")
            checksum = sha256(sql.encode("utf-8")).hexdigest()
            row = conn.execute(
                "SELECT checksum FROM og_schema_migrations WHERE version = %s", (path.name,)
            ).fetchone()
            if row:
                if row[0] != checksum:
                    raise ValueError(f"Applied migration changed: {path.name}")
                continue
            conn.execute(sql)
            conn.execute(
                "INSERT INTO og_schema_migrations (version, checksum) VALUES (%s, %s)",
                (path.name, checksum),
            )
            applied.append(path.name)
    return applied


if __name__ == "__main__":
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is required to run migrations")
    print("Applied migrations:", ", ".join(apply_migrations(settings.database_url)) or "none")
