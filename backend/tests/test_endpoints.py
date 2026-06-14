"""Integration tests for FastAPI routes using in-memory fixtures."""
import json, os, pytest
from pathlib import Path
from fastapi.testclient import TestClient


FIXTURE_EVENT = {
    "id": "bar-reef-003",
    "source": "GFW",
    "lat": 8.51, "lon": 79.68,
    "risk_score": 0.61, "risk_level": "HIGH",
    "sar_confidence": 0.70, "image_quality": "Good",
    "ais_matched": False, "ais_data_available": True,
    "matching_method": "Spatial 2km + 3hr time window",
    "inside_mpa": False, "near_mpa": True,
    "mpa_name": "Bar Reef Marine Sanctuary",
    "distance_to_mpa_km": 0.4, "distance_from_port_km": 33.1,
    "nearest_port": "Marina (OSM)",
    "timestamp": "2026-06-09T14:32:00Z",
    "review_status": "Pending",
    "why_flagged": "", "uncertainty": "",
    "confidence_threshold": 0.45,
    "recommended_action": "Human reviewer should verify scene.",
    "thumbnail": None,
}

FIXTURE_METRICS = {
    "model": "YOLO11n", "dataset": "HRSID", "epochs": 50,
    "map50": 0.838, "map50_95": 0.579, "precision": 0.830, "recall": 0.818,
    "confidence_threshold": 0.45, "validation_scene": "xView3",
    "detections_on_real_scene": 122, "training_history": [],
}

FIXTURE_GEOJSON = {
    "type": "Feature",
    "geometry": {"type": "Polygon", "coordinates": [[[79.7, 8.3], [79.8, 8.5], [79.6, 8.5], [79.7, 8.3]]]},
    "properties": {"NAME": "Bar Reef"},
}


@pytest.fixture
def client(tmp_path):
    (tmp_path / "risk_events.json").write_text(json.dumps([FIXTURE_EVENT]))
    (tmp_path / "metrics.json").write_text(json.dumps(FIXTURE_METRICS))
    (tmp_path / "bar_reef.geojson").write_text(json.dumps(FIXTURE_GEOJSON))
    (tmp_path / "ports.json").write_text(json.dumps([{"name": "Marina", "lat": 8.21, "lon": 79.70}]))

    # Patch settings and reload store
    from unittest.mock import patch
    with patch("app.core.config.settings") as mock_cfg:
        mock_cfg.data_dir = tmp_path
        mock_cfg.anthropic_api_key = ""
        # Re-import app after patching
        from app.store.repository import repo
        repo._events = {}
        repo.load()
        from app.main import app
        yield TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_list_risk_events(client):
    r = client.get("/risk-events")
    assert r.status_code == 200
    assert r.json()[0]["id"] == "bar-reef-003"


def test_get_single_event(client):
    r = client.get("/risk-events/bar-reef-003")
    assert r.status_code == 200
    assert r.json()["risk_score"] == 0.61


def test_event_not_found(client):
    assert client.get("/risk-events/no-such").status_code == 404


def test_filter_source(client):
    r = client.get("/risk-events?source=GFW")
    assert all(e["source"] == "GFW" for e in r.json())


def test_filter_level(client):
    r = client.get("/risk-events?level=HIGH")
    assert all(e["risk_level"] == "HIGH" for e in r.json())


def test_update_review(client):
    r = client.post("/risk-events/bar-reef-003/review", json={"review_status": "Confirmed Risk"})
    assert r.status_code == 200
    assert r.json()["review_status"] == "Confirmed Risk"


def test_update_review_not_found(client):
    assert client.post("/risk-events/nope/review", json={"review_status": "Pending"}).status_code == 404


def test_metrics(client):
    r = client.get("/model-metrics")
    assert r.status_code == 200
    assert r.json()["map50"] == 0.838


def test_mpa(client):
    r = client.get("/mpa")
    assert r.status_code == 200
    assert r.json()["type"] == "Feature"


def test_narrate_fallback(client):
    r = client.post("/agents/narrate", json=FIXTURE_EVENT)
    assert r.status_code == 200
    body = r.json()
    assert len(body.get("why_flagged", "")) > 10
    assert "uncertainty" in body


def test_briefing_fallback(client):
    r = client.post("/agents/briefing", json=[FIXTURE_EVENT])
    assert r.status_code == 200
    assert len(r.json().get("briefing", "")) > 10


def test_patrol_fallback(client):
    r = client.post("/agents/patrol", json=[FIXTURE_EVENT])
    assert r.status_code == 200
    items = r.json()
    assert items[0]["rank"] == 1
    assert items[0]["id"] == "bar-reef-003"


def test_ask_fallback(client):
    r = client.post("/agents/ask", json={"question": "Which detection is highest risk?"})
    assert r.status_code == 200
    assert "bar-reef-003" in r.json()["answer"]
