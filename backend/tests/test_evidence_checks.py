from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

from fastapi.testclient import TestClient

from app.services.ais_stream import sample_association
from app.services import gfw_ingest
from app.store.activity import ActivityStore
from .test_endpoints import client


def _time(offset_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def test_empty_ais_sample_is_unavailable() -> None:
    assert sample_association(8.5, 79.6, _time(), []) == ("unavailable", [])


def test_old_observation_is_not_matched_to_live_ais() -> None:
    vessel = {"mmsi": "123", "lat": 8.5, "lon": 79.6, "timestamp": _time()}
    assert sample_association(8.5, 79.6, _time(-3600), [vessel]) == ("unavailable", [])


def test_recent_ais_candidates_can_be_ambiguous() -> None:
    vessels = [
        {"mmsi": mmsi, "lat": 8.5, "lon": 79.6, "timestamp": _time()}
        for mmsi in ("123", "456")
    ]
    assert sample_association(8.5, 79.6, _time(), vessels) == ("ambiguous", ["123", "456"])


def test_no_nearby_ais_does_not_confirm_dark() -> None:
    vessel = {"mmsi": "123", "lat": 10.0, "lon": 80.0, "timestamp": _time()}
    assert sample_association(8.5, 79.6, _time(), [vessel]) == ("unavailable", [])


def test_ais_route_does_not_confirm_aggregate_as_dark(client: TestClient) -> None:
    with patch("app.api.routes.ais.ais_stream.ais_enabled", return_value=True), patch(
        "app.api.routes.ais.ais_stream.collect_ais", return_value=[]
    ):
        response = client.post("/ais/verify-dark?seconds=5")
    assert response.status_code == 200
    assert response.json()["dark_confirmed"] == 0
    assert response.json()["results"][0]["association_status"] == "unavailable"


def test_repeated_yolo_scan_never_inflates_risk(client: TestClient) -> None:
    result = {
        "found": True,
        "detections": [{"lat": 8.51, "lon": 79.68, "confidence": 0.9}],
    }
    response = Mock()
    response.json.return_value = result
    response.raise_for_status.return_value = None
    with patch("app.api.routes.verify.settings.yolo_service_url", "https://example.invalid"), patch(
        "app.api.routes.verify.httpx.post", return_value=response
    ):
        for _ in range(2):
            check = client.post(
                "/verify/yolo",
                params={
                    "lat": 8.51,
                    "lon": 79.68,
                    "date": "2026-06-09T14:32:00Z",
                    "event_id": "bar-reef-003",
                },
            )
            assert check.status_code == 200
            assert check.json()["agreement"] is False
            assert check.json()["spatial_match"] is True
            assert check.json()["updated_event"] is None
    assert client.get("/risk-events/bar-reef-003").json()["risk_score"] == 0.61


def test_yolo_result_exposes_unverified_scene_provenance(client: TestClient) -> None:
    response = Mock()
    response.json.return_value = {
        "found": False, "detections": [], "count": 0,
        "best_confidence": 0, "chip_px": 384,
        "chip_bbox": [79.6, 8.5, 79.7, 8.6], "chip_png_b64": "", "conf_threshold": 0.35,
    }
    response.raise_for_status.return_value = None
    with patch("app.api.routes.verify.settings.yolo_service_url", "https://example.invalid"), patch(
        "app.api.routes.verify.httpx.post", return_value=response
    ):
        result = client.post("/verify/yolo", params={
            "lat": 8.5, "lon": 79.6, "date": "2026-06-09T14:32:00Z",
        })
    assert result.status_code == 200
    assert result.json()["provenance"]["coverage_status"] == "scene_time_unverified"
    assert result.json()["provenance"]["acquisition_id"] is None


def test_yolo_rejects_invalid_acquisition_time(client: TestClient) -> None:
    with patch("app.api.routes.verify.settings.yolo_service_url", "https://example.invalid"):
        result = client.post("/verify/yolo", params={
            "lat": 8.5, "lon": 79.6, "date": "not-a-date",
        })
    assert result.status_code == 422


def test_gfw_report_rows_remain_distinct_aggregates() -> None:
    rows = [
        {"lat": 8.5, "lon": 79.6, "detections": 2},
        {"lat": 8.5, "lon": 79.6, "detections": 3},
    ]
    with patch.object(gfw_ingest, "_fetch_sar_report", return_value=(rows, "2026-06-01", "2026-06-08")):
        activity = gfw_ingest.fetch_activity()
    assert len(activity) == 2
    assert activity[0].id != activity[1].id
    assert [cell.detection_count for cell in activity] == [2, 3]
    assert all(cell.provider_time is None for cell in activity)
    assert all(cell.report_end == "2026-06-08" for cell in activity)


def test_gfw_report_accepts_flat_and_grouped_rows() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "entries": [
            {"lat": 8.5, "lon": 79.6, "detections": 2},
            {"public-global-sar-presence:v4": [
                {"lat": 8.6, "lon": 79.7, "detections": 3},
            ]},
        ]
    }
    client = MagicMock()
    client.post.return_value = response
    client.__enter__.return_value = client
    with patch.object(gfw_ingest.httpx, "Client", return_value=client):
        rows, _, _ = gfw_ingest._fetch_sar_report()
    assert len(rows) == 2


def test_activity_failure_preserves_last_success() -> None:
    store = ActivityStore()
    with patch.object(gfw_ingest, "_fetch_sar_report", return_value=(
        [{"lat": 8.5, "lon": 79.6, "detections": 2}], "2026-06-01", "2026-06-08"
    )):
        store.replace(gfw_ingest.fetch_activity())
    store.failure(ValueError("bad response"))
    page = store.page()
    assert page.data_state == "stale"
    assert page.total == 1
    assert store.status()["error_category"] == "invalid_response"
    assert store.page(bbox=(79.5, 8.4, 79.7, 8.6)).total == 1
    assert store.page(bbox=(0, 0, 1, 1)).total == 0


def test_gfw_activity_api_does_not_replace_sample_events(client: TestClient) -> None:
    with patch("app.api.routes.ingest.activity_store", ActivityStore()), patch(
        "app.api.routes.ingest.gfw_ingest.ingestion_enabled", return_value=True
    ), patch(
        "app.api.routes.ingest.gfw_ingest.fetch_activity", return_value=[]
    ):
        response = client.post("/ingest/gfw")
        assert response.status_code == 200
        assert response.json()["record_type"] == "activity_aggregate"
        assert client.get("/risk-events/bar-reef-003").status_code == 200
        assert client.get("/activity/gfw?limit=5").json()["data_state"] == "empty"
