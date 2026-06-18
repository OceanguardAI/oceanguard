from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

FIXTURE_EVENT = {
    "id": "bar-reef-003",
    "source": "GFW",
    "lat": 8.51,
    "lon": 79.68,
    "risk_score": 0.61,
    "risk_level": "HIGH",
    "sar_confidence": 0.70,
    "image_quality": "Good",
    "ais_matched": False,
    "ais_data_available": True,
    "matching_method": "Spatial 2km + 3hr time window",
    "inside_mpa": False,
    "near_mpa": True,
    "mpa_name": "Bar Reef Marine Sanctuary",
    "distance_to_mpa_km": 0.4,
    "distance_from_port_km": 33.1,
    "nearest_port": "Marina (OSM)",
    "timestamp": "2026-06-09T14:32:00Z",
    "review_status": "Pending",
    "why_flagged": "",
    "uncertainty": "",
    "confidence_threshold": 0.45,
    "recommended_action": "Human reviewer should verify scene and external context.",
    "thumbnail": None,
}

FIXTURE_METRICS = {
    "model": "YOLO11n",
    "dataset": "HRSID",
    "epochs": 50,
    "map50": 0.838,
    "map50_95": 0.579,
    "precision": 0.830,
    "recall": 0.818,
    "confidence_threshold": 0.45,
    "validation_scene": "xView3",
    "detections_on_real_scene": 122,
    "training_history": [],
}

FIXTURE_GEOJSON = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[79.7, 8.3], [79.8, 8.5], [79.6, 8.5], [79.7, 8.3]]],
    },
    "properties": {"NAME": "Bar Reef"},
}


@pytest.fixture
def client(tmp_path: Path):
    (tmp_path / "risk_events.json").write_text(json.dumps([FIXTURE_EVENT]), encoding="utf-8")
    (tmp_path / "metrics.json").write_text(json.dumps(FIXTURE_METRICS), encoding="utf-8")
    (tmp_path / "bar_reef.geojson").write_text(json.dumps(FIXTURE_GEOJSON), encoding="utf-8")
    (tmp_path / "ports.json").write_text(
        json.dumps([{"name": "Marina", "lat": 8.21, "lon": 79.70}]),
        encoding="utf-8",
    )

    with patch("app.core.config.settings.data_dir", tmp_path), patch(
        "app.core.config.settings.gemini_api_key", ""
    ), patch(
        "app.core.config.settings.gemini_use_gcp", False
    ), patch(
        "app.core.config.settings.google_genai_use_vertexai", False
    ), patch(
        "app.core.config.settings.gfw_ingest_on_startup", False
    ):
        from app.store.repository import repo

        repo._events = {}
        repo.load()

        from app.main import app

        with TestClient(app) as test_client:
            yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["events_loaded"] == 1


def test_list_risk_events(client: TestClient) -> None:
    response = client.get("/risk-events")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "bar-reef-003"


def test_get_single_event(client: TestClient) -> None:
    response = client.get("/risk-events/bar-reef-003")
    assert response.status_code == 200
    assert response.json()["risk_score"] == 0.61


def test_event_not_found(client: TestClient) -> None:
    assert client.get("/risk-events/no-such").status_code == 404


def test_filter_source(client: TestClient) -> None:
    response = client.get("/risk-events?source=GFW")
    assert all(item["source"] == "GFW" for item in response.json())


def test_filter_level(client: TestClient) -> None:
    response = client.get("/risk-events?level=HIGH")
    assert all(item["risk_level"] == "HIGH" for item in response.json())


def test_risk_summary(client: TestClient) -> None:
    response = client.get("/risk-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["total_events"] == 1
    assert body["source_counts"]["GFW"] == 1
    assert body["highest_risk_event_id"] == "bar-reef-003"


def test_update_review(client: TestClient) -> None:
    response = client.post(
        "/risk-events/bar-reef-003/review",
        json={"review_status": "Confirmed Risk"},
    )
    assert response.status_code == 200
    assert response.json()["review_status"] == "Confirmed Risk"


def test_filter_review_status(client: TestClient) -> None:
    client.post(
        "/risk-events/bar-reef-003/review",
        json={"review_status": "Confirmed Risk"},
    )
    response = client.get("/risk-events?review_status=Confirmed Risk")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["bar-reef-003"]


def test_update_review_persists_to_disk(client: TestClient) -> None:
    response = client.post(
        "/risk-events/bar-reef-003/review",
        json={"review_status": "Resolved"},
    )
    assert response.status_code == 200

    from app.core.config import settings

    persisted = json.loads((settings.data_dir / "risk_events.json").read_text(encoding="utf-8"))
    assert persisted[0]["review_status"] == "Resolved"


def test_metrics(client: TestClient) -> None:
    response = client.get("/model-metrics")
    assert response.status_code == 200
    assert response.json()["map50"] == 0.838


def test_mpa(client: TestClient) -> None:
    response = client.get("/mpa")
    assert response.status_code == 200
    assert response.json()["type"] == "Feature"


def test_mpa_missing_file_returns_503(client: TestClient) -> None:
    from app.core.config import settings

    (settings.data_dir / "bar_reef.geojson").unlink()
    response = client.get("/mpa")
    assert response.status_code == 503
    assert "Run the ML sync step" in response.json()["detail"]


def test_ports(client: TestClient) -> None:
    response = client.get("/ports")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Marina"


def test_ports_missing_file_returns_503(client: TestClient) -> None:
    from app.core.config import settings

    (settings.data_dir / "ports.json").unlink()
    response = client.get("/ports")
    assert response.status_code == 503
    assert "Run the ML sync step" in response.json()["detail"]


def test_cors_preflight_health(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_narrate_fallback(client: TestClient) -> None:
    response = client.post("/agents/narrate", json=FIXTURE_EVENT)
    assert response.status_code == 200
    body = response.json()
    assert len(body["why_flagged"]) > 10
    assert "uncertainty" in body


def test_agent_status_without_api_key(client: TestClient) -> None:
    response = client.get("/agents/status")
    assert response.status_code == 200
    body = response.json()
    from app.agents.client import genai_importable

    assert body["provider"] == "gemini"
    assert body["provider_mode"] == "api_key"
    assert body["provider_enabled"] is False
    assert body["provider_importable"] is genai_importable()
    assert body["client_ready"] is False
    assert body["fallback_mode"] is True
    from app.core.config import settings

    assert body["model"] == settings.gemini_model
    assert body["agent_max_tool_rounds"] == 5
    assert body["agent_narrator_max_tokens"] == 500
    assert body["agent_briefing_max_tokens"] == 400
    assert body["agent_patrol_max_tokens"] == 600
    assert body["agent_ask_max_tokens"] == 700


def test_narrate_loaded_event_fallback(client: TestClient) -> None:
    response = client.post("/agents/narrate/bar-reef-003")
    assert response.status_code == 200
    assert "why_flagged" in response.json()


def test_narrate_loaded_event_not_found(client: TestClient) -> None:
    response = client.post("/agents/narrate/no-such")
    assert response.status_code == 404


def test_briefing_fallback(client: TestClient) -> None:
    response = client.post("/agents/briefing", json=[FIXTURE_EVENT])
    assert response.status_code == 200
    assert len(response.json()["briefing"]) > 10


def test_briefing_current_from_repo(client: TestClient) -> None:
    response = client.post("/agents/briefing/current?source=GFW")
    assert response.status_code == 200
    assert "bar-reef-003" in response.json()["briefing"]


def test_patrol_fallback(client: TestClient) -> None:
    response = client.post("/agents/patrol", json=[FIXTURE_EVENT])
    assert response.status_code == 200
    body = response.json()
    assert body[0]["rank"] == 1
    assert body[0]["id"] == "bar-reef-003"


def test_patrol_current_from_repo(client: TestClient) -> None:
    response = client.post("/agents/patrol/current?review_status=Pending")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["rank"] == 1
    assert body[0]["id"] == "bar-reef-003"


def test_ask_fallback(client: TestClient) -> None:
    response = client.post("/agents/ask", json={"question": "Which detection is highest risk?"})
    assert response.status_code == 200
    assert "bar-reef-003" in response.json()["answer"]


def test_ask_fallback_counts(client: TestClient) -> None:
    response = client.post("/agents/ask", json={"question": "How many detections are loaded?"})
    assert response.status_code == 200
    assert "1 total events" in response.json()["answer"]


def test_ask_fallback_model_metrics(client: TestClient) -> None:
    response = client.post("/agents/ask", json={"question": "What is the model map50?"})
    assert response.status_code == 200
    assert "map50=0.838" in response.json()["answer"]


def test_metrics_missing_file_returns_503(client: TestClient) -> None:
    from app.core.config import settings

    (settings.data_dir / "metrics.json").unlink()
    response = client.get("/model-metrics")
    assert response.status_code == 503
    assert "Run the ML sync step" in response.json()["detail"]


def test_ask_fallback_ports(client: TestClient) -> None:
    response = client.post("/agents/ask", json={"question": "Which marina is in the backend data?"})
    assert response.status_code == 200
    assert "Marina" in response.json()["answer"]
