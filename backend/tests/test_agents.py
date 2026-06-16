from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from app.agents import ask, briefing, narrator, patrol
from app.models.schemas import RiskEvent
from app.store.repository import repo


def _event(**overrides) -> RiskEvent:
    payload = {
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
    payload.update(overrides)
    return RiskEvent(**payload)


class _FakeClient:
    def __init__(self, response):
        self.messages = SimpleNamespace(create=lambda **_: response)


def test_narrator_parses_valid_json_response(monkeypatch) -> None:
    response = SimpleNamespace(
        content=[
            SimpleNamespace(
                text='{"why_flagged":"Possible dark vessel.","uncertainty":"Needs review."}'
            )
        ]
    )
    monkeypatch.setattr(narrator, "get_client", lambda: _FakeClient(response))

    result = asyncio.run(narrator.narrate(_event()))

    assert result.why_flagged == "Possible dark vessel."
    assert result.uncertainty == "Needs review."


def test_narrator_falls_back_on_incomplete_json(monkeypatch) -> None:
    response = SimpleNamespace(content=[SimpleNamespace(text='{"why_flagged":"Only one field"}')])
    monkeypatch.setattr(narrator, "get_client", lambda: _FakeClient(response))

    result = asyncio.run(narrator.narrate(_event()))

    assert "decision-support lead" in result.uncertainty


def test_briefing_falls_back_on_blank_model_text(monkeypatch) -> None:
    response = SimpleNamespace(content=[SimpleNamespace(text="   ")])
    monkeypatch.setattr(briefing, "get_client", lambda: _FakeClient(response))

    result = asyncio.run(briefing.briefing([_event()]))

    assert "OceanGuard is tracking 1 current detections" in result.briefing


def test_patrol_falls_back_on_invalid_json(monkeypatch) -> None:
    response = SimpleNamespace(content=[SimpleNamespace(text="not-json")])
    monkeypatch.setattr(patrol, "get_client", lambda: _FakeClient(response))

    result = asyncio.run(
        patrol.patrol(
            [
                _event(id="bar-reef-003", risk_score=0.61, near_mpa=True),
                _event(id="bar-reef-001", risk_score=0.46, near_mpa=False, distance_to_mpa_km=14.1),
            ]
        )
    )

    assert result[0].id == "bar-reef-003"
    assert result[0].rank == 1


def test_ask_tool_query_detections_includes_review_status() -> None:
    original_events = repo._events.copy()
    try:
        event = _event(review_status="Resolved")
        repo._events = {event.id: event}
        text = ask._run_tool("query_detections", {"review_status": "Resolved"})
    finally:
        repo._events = original_events

    assert "Found 1 event(s):" in text
    assert "review=Resolved" in text


def test_ask_fallback_review_counts(monkeypatch, tmp_path: Path) -> None:
    original_events = repo._events.copy()
    original_data_dir = ask.settings.data_dir
    try:
        event = _event(review_status="Resolved")
        repo._events = {event.id: event}
        ask.settings.data_dir = tmp_path
        result = ask._fallback("How many reviews are resolved?")
    finally:
        repo._events = original_events
        ask.settings.data_dir = original_data_dir

    assert "Resolved=1" in result.answer
