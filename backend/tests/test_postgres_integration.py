"""Run only against a dedicated disposable PostGIS database."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.schemas import ActivityAggregate, RiskEvent
from app.store.activity import PostgresActivityStore
from app.store.migrate import apply_migrations
from app.store.postgres import PostgresRiskEventRepository
from .test_endpoints import FIXTURE_EVENT


TEST_DSN = os.getenv("OCEANGUARD_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DSN, reason="Dedicated PostGIS test database not configured")


def test_migration_restart_review_and_activity_survive_new_instances() -> None:
    assert TEST_DSN is not None
    apply_migrations(TEST_DSN)
    assert apply_migrations(TEST_DSN) == []

    event_id = f"integration-{uuid4()}"
    event = RiskEvent.model_validate({**FIXTURE_EVENT, "id": event_id, "source": "YOLO_SAR"})
    first = PostgresRiskEventRepository(TEST_DSN)
    first.load()
    first.upsert_many([event])
    assert first.update_review(event_id, "Confirmed Risk").review_status == "Confirmed Risk"

    second = PostgresRiskEventRepository(TEST_DSN)
    second.load()
    assert second.get(event_id).review_status == "Confirmed Risk"
    assert second.review_history(event_id)[0].storage_scope == "database"
    second.upsert_many([event.model_copy(update={"risk_score": 0.99})])
    assert second.get(event_id).review_status == "Confirmed Risk"
    assert second.get(event_id).risk_score == event.risk_score

    activity = ActivityAggregate(
        id=f"integration-{uuid4()}", dataset="test-sar", lat=8.5, lon=79.6,
        detection_count=2, report_start="2026-09-01", report_end="2026-09-08",
        provider_time=None, ingested_at=datetime.now(timezone.utc),
    )
    source = PostgresActivityStore(TEST_DSN)
    source.replace([activity])
    restarted = PostgresActivityStore(TEST_DSN)
    page = restarted.page(bbox=(79.5, 8.4, 79.7, 8.6))
    assert page.total == 1
    assert page.items[0].id == activity.id
    restarted.failure(ValueError("invalid provider response"))
    assert PostgresActivityStore(TEST_DSN).page().data_state == "stale"
