"""Run GFW refreshes in a finite, separately scheduled worker process."""
from __future__ import annotations

import argparse
import sys
from typing import Literal

from app.core.config import settings
from app.jobs.queue import PostgresJobQueue, daily_gfw_key
from app.services import gfw_ingest
from app.store.activity import PostgresActivityStore, _error_category


def run_once(
    queue: PostgresJobQueue, activity: PostgresActivityStore,
) -> Literal["idle", "succeeded", "retry"]:
    job = queue.claim()
    if job is None:
        return "idle"
    try:
        rows = gfw_ingest.fetch_activity()
    except Exception as exc:
        category = _error_category(exc)
        if not queue.fail(job, category):
            raise RuntimeError("GFW job lease expired during failure handling") from exc
        return "retry"
    try:
        completed = queue.complete_gfw(job, activity, rows)
    except Exception as exc:
        if not queue.fail(job, "storage_unavailable"):
            raise RuntimeError("GFW job lease expired during storage failure") from exc
        return "retry"
    if not completed:
        raise RuntimeError("GFW job lease expired before completion")
    return "succeeded"


def main() -> int:
    parser = argparse.ArgumentParser(description="OceanGuard durable GFW refresh jobs")
    sub = parser.add_subparsers(dest="command", required=True)
    enqueue = sub.add_parser("enqueue-gfw")
    enqueue.add_argument("--key", help="stable deduplication key; defaults to current UTC day")
    sub.add_parser("run-once")
    args = parser.parse_args()
    if not settings.database_url:
        parser.error("DATABASE_URL is required; run migrations first")
    queue = PostgresJobQueue(settings.database_url)
    if args.command == "enqueue-gfw":
        print(queue.enqueue_gfw(args.key or daily_gfw_key()))
        return 0
    if not gfw_ingest.ingestion_enabled():
        parser.error("GFW_API_TOKEN is required to run a refresh")
    outcome = run_once(queue, PostgresActivityStore(settings.database_url))
    print(outcome)
    return 1 if outcome == "retry" else 0


if __name__ == "__main__":
    sys.exit(main())
