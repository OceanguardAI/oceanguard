from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.services import gfw_ingest
from app.store.activity import _snapshot_id
from app.store.postgres import PostgresRiskEventRepository
from app.store.repository import repo
from .test_endpoints import client


def test_review_history_records_each_transition(client: TestClient) -> None:
    first = client.post(
        "/risk-events/bar-reef-003/review", json={"review_status": "Confirmed Risk"}
    )
    second = client.post(
        "/risk-events/bar-reef-003/review", json={"review_status": "Resolved"}
    )
    history = client.get("/risk-events/bar-reef-003/reviews")

    assert first.status_code == second.status_code == history.status_code == 200
    assert [(r["previous_status"], r["review_status"]) for r in history.json()] == [
        ("Pending", "Confirmed Risk"), ("Confirmed Risk", "Resolved")
    ]
    assert all(r["storage_scope"] == "process_local" for r in history.json())


def test_failed_local_review_does_not_change_case(client: TestClient) -> None:
    with patch.object(repo, "save", side_effect=OSError("disk unavailable")):
        with pytest.raises(OSError):
            repo.update_review("bar-reef-003", "Resolved")
    assert repo.get("bar-reef-003").review_status == "Pending"
    assert repo.review_history("bar-reef-003") == []


def test_durable_repository_rejects_history_replacement() -> None:
    durable = PostgresRiskEventRepository("postgresql://unused")
    with pytest.raises(ValueError, match="Replacing durable case history"):
        durable.replace_all([])


def test_replace_api_rejected_in_database_mode(client: TestClient) -> None:
    with patch("app.api.routes.ingest.settings.database_url", "postgresql://unused"):
        response = client.post("/ingest/push?mode=replace", json=[])
    assert response.status_code == 409


def test_activity_bbox_rejects_nonfinite_coordinates(client: TestClient) -> None:
    response = client.get("/activity/gfw?bbox=nan,0,10,10")
    assert response.status_code == 422


def test_gfw_row_and_snapshot_ids_ignore_provider_row_order() -> None:
    rows = [
        {"lat": 8.5, "lon": 79.6, "detections": 2},
        {"lat": 8.5, "lon": 79.6, "detections": 3},
    ]
    with patch.object(gfw_ingest, "_fetch_sar_report", return_value=(rows, "2026-09-01", "2026-09-08")):
        first = gfw_ingest.fetch_activity()
    with patch.object(gfw_ingest, "_fetch_sar_report", return_value=(
        list(reversed(rows)), "2026-09-01", "2026-09-08"
    )):
        second = gfw_ingest.fetch_activity()
    assert {item.id for item in first} == {item.id for item in second}
    assert _snapshot_id(first) == _snapshot_id(second)
