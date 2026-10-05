from __future__ import annotations

import asyncio
from pathlib import Path

from app.agents import ask, briefing, helpers, narrator, patrol
from app.models.schemas import RiskEvent
from app.store.repository import repo
from tests.groq_fakes import FakeGroq, reply


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


def test_narrator_parses_valid_json_response(monkeypatch) -> None:
    fake = FakeGroq(reply('{"why_flagged":"Possible dark vessel.","uncertainty":"Needs review."}'))
    monkeypatch.setattr(narrator, "get_client", lambda: fake)

    result = asyncio.run(narrator.narrate(_event()))

    assert result.why_flagged == "Possible dark vessel."
    assert result.uncertainty == "Needs review."


def test_narrator_falls_back_on_incomplete_json(monkeypatch) -> None:
    fake = FakeGroq(reply('{"why_flagged":"Only one field"}'))
    monkeypatch.setattr(narrator, "get_client", lambda: fake)

    result = asyncio.run(narrator.narrate(_event()))

    assert "decision-support lead" in result.uncertainty


def test_briefing_falls_back_on_blank_model_text(monkeypatch) -> None:
    fake = FakeGroq(reply("   "))
    monkeypatch.setattr(briefing, "get_client", lambda: fake)

    result = asyncio.run(briefing.briefing([_event()]))

    assert "OceanGuard is tracking 1 current detections" in result.briefing


def test_patrol_falls_back_on_invalid_json(monkeypatch) -> None:
    fake = FakeGroq(reply("not-json"))
    monkeypatch.setattr(patrol, "get_client", lambda: fake)

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


def test_patrol_zero_distance_stays_highest_priority_on_ties() -> None:
    result = patrol._deterministic_rank(
        [
            _event(id="boundary", risk_score=0.61, near_mpa=True, inside_mpa=False, distance_to_mpa_km=0.0),
            _event(id="farther", risk_score=0.61, near_mpa=True, inside_mpa=False, distance_to_mpa_km=1.2),
        ]
    )

    assert result[0].id == "boundary"


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


def test_ask_get_event_tool_requires_id() -> None:
    text = ask._run_tool("get_event", {})
    assert "missing required 'id' field" in text


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


def test_ask_uses_configured_model_and_max_tokens(monkeypatch) -> None:
    fake = FakeGroq(reply("Configured."))
    monkeypatch.setattr(ask, "get_client", lambda: fake)
    monkeypatch.setattr(ask.settings, "groq_model", "test-model")
    monkeypatch.setattr(ask.settings, "agent_ask_max_tokens", 321)

    result = asyncio.run(ask.ask("hello"))

    assert result.answer == "Configured."
    assert len(fake.requests) == 1
    assert fake.requests[0]["model"] == "test-model"
    assert fake.requests[0]["max_tokens"] == 321


def test_ask_stops_at_the_tool_round_limit(monkeypatch) -> None:
    fake = FakeGroq(reply(None, tool_calls=[("call_1", "get_risk_summary", {})]))
    monkeypatch.setattr(ask, "get_client", lambda: fake)
    monkeypatch.setattr(ask.settings, "agent_max_tool_rounds", 2)

    result = asyncio.run(ask.ask("how many?"))

    assert len(fake.requests) == 2
    assert result == ask._fallback("how many?")


def test_ask_tool_loop_executes_tool_and_returns_final_answer(monkeypatch) -> None:
    original_events = repo._events.copy()
    fake = FakeGroq(
        reply(None, tool_calls=[("call_1", "get_event", {"id": "bar-reef-003"})]),
        reply("bar-reef-003 remains the highest-risk reviewed lead."),
    )
    try:
        event = _event(review_status="Resolved")
        repo._events = {event.id: event}
        monkeypatch.setattr(ask, "get_client", lambda: fake)

        result = asyncio.run(ask.ask("Give me the latest details for bar-reef-003"))
    finally:
        repo._events = original_events

    assert result.answer == "bar-reef-003 remains the highest-risk reviewed lead."
    assert len(fake.requests) == 2
    tool_message = fake.requests[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call_1"
    assert '"review_status": "Resolved"' in tool_message["content"]


def test_ask_fallback_specific_event_uses_repo_data() -> None:
    original_events = repo._events.copy()
    try:
        event = _event(review_status="Resolved", risk_score=0.77, risk_level="CRITICAL")
        repo._events = {event.id: event}
        result = ask._fallback("What is the current status of bar-reef-003?")
    finally:
        repo._events = original_events

    assert "0.77 (CRITICAL)" in result.answer
    assert "review status Resolved" in result.answer
    assert "Recommended action" in result.answer


def test_ask_fallback_highest_risk_uses_live_repo_data() -> None:
    original_events = repo._events.copy()
    try:
        low = _event(id="bar-reef-001", risk_score=0.20, risk_level="LOW")
        top = _event(
            id="bar-reef-999",
            risk_score=0.91,
            risk_level="CRITICAL",
            ais_matched=True,
            distance_to_mpa_km=2.4,
            mpa_name="Custom Reef Boundary",
        )
        repo._events = {low.id: low, top.id: top}
        result = ask._fallback("Which detection is highest risk?")
    finally:
        repo._events = original_events

    assert "bar-reef-999" in result.answer
    assert "0.91 (CRITICAL)" in result.answer
    assert "an AIS match" in result.answer
    assert "2.4 km from Custom Reef Boundary" in result.answer


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
    fake = FakeGroq(reply("[]"))
    monkeypatch.setattr(patrol, "get_client", lambda: fake)

    result = asyncio.run(patrol.patrol([_event()]))

    prompt = fake.requests[0]["messages"][-1]["content"]
    assert result[0].id == "bar-reef-003"
    assert "Prioritise higher risk_score first" in prompt
    assert "review_status=Pending" in prompt
    assert "response_format" not in fake.requests[0]
