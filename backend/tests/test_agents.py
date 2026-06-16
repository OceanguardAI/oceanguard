from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from app.agents import ask, briefing, helpers, narrator, patrol
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
    assert "review_status=Resolved" in text


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


def test_ask_uses_configured_model_and_tool_round_limit(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(text="Configured.")])

    original_model = ask.settings.anthropic_model
    original_rounds = ask.settings.agent_max_tool_rounds
    try:
        ask.settings.anthropic_model = "claude-test-model"
        ask.settings.agent_max_tool_rounds = 1
        monkeypatch.setattr(
            ask,
            "get_client",
            lambda: SimpleNamespace(messages=SimpleNamespace(create=fake_create)),
        )

        result = asyncio.run(ask.ask("hello"))
    finally:
        ask.settings.anthropic_model = original_model
        ask.settings.agent_max_tool_rounds = original_rounds

    assert result.answer == "Configured."
    assert len(calls) == 1
    assert calls[0]["model"] == "claude-test-model"


def test_event_summary_line_includes_core_context() -> None:
    line = helpers.event_summary_line(_event(review_status="Resolved"), include_review=True)
    assert "bar-reef-003" in line
    assert "risk=HIGH (0.61)" in line
    assert "review_status=Resolved" in line


def test_build_event_context_sorts_by_risk() -> None:
    text = helpers.build_event_context(
        [
            _event(id="low", risk_score=0.20, risk_level="LOW"),
            _event(id="high", risk_score=0.90, risk_level="CRITICAL"),
        ],
        include_review=True,
    )
    first_line = text.splitlines()[0]
    assert "high" in first_line


def test_narrator_prompt_includes_recommended_action() -> None:
    prompt = narrator._build_user_prompt(_event())
    assert "Recommended action:" in prompt
    assert "Event summary:" in prompt


def test_briefing_prompt_includes_alertness_and_context() -> None:
    prompt = briefing._build_user_prompt([_event()])
    assert "Recommended alertness baseline:" in prompt
    assert "Top detections by risk:" in prompt


def test_patrol_prompt_context_lists_detections(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_create(**kwargs):
        captured["content"] = kwargs["messages"][0]["content"]
        return SimpleNamespace(content=[SimpleNamespace(text="[]")])

    monkeypatch.setattr(
        patrol,
        "get_client",
        lambda: SimpleNamespace(messages=SimpleNamespace(create=fake_create)),
    )

    result = asyncio.run(patrol.patrol([_event()]))

    assert result[0].id == "bar-reef-003"
    assert "Prioritise higher risk_score first" in captured["content"]
    assert "review_status=Pending" in captured["content"]
