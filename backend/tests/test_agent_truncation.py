"""A model response cut off by the token budget must never be shown as finished."""
from __future__ import annotations

import asyncio

from app.agents import ask, briefing
from app.agents.helpers import trim_to_last_sentence
from app.models.schemas import RiskEvent
from tests.groq_fakes import FakeGroq, reply


def _event() -> RiskEvent:
    return RiskEvent(
        id="e-1", source="GFW", lat=8.5, lon=79.6, risk_score=0.6, risk_level="HIGH",
        sar_confidence=0.7, image_quality="Good", ais_matched=False, ais_data_available=True,
        matching_method="m", inside_mpa=False, near_mpa=True, mpa_name="MPA",
        distance_to_mpa_km=1.0, distance_from_port_km=5.0, nearest_port="P",
        timestamp="2026-10-01T00:00:00Z", review_status="Pending", why_flagged="",
        uncertainty="", confidence_threshold=0.45, recommended_action="Review.", thumbnail=None,
    )


def test_trim_keeps_only_complete_sentences() -> None:
    assert trim_to_last_sentence("One. Two. Thre") == "One. Two."
    assert trim_to_last_sentence("Complete sentence.") == "Complete sentence."
    assert trim_to_last_sentence('He said "stop." Then') == 'He said "stop."'
    assert trim_to_last_sentence("For June 22, 2026") == ""
    assert trim_to_last_sentence("Distance is 0.5 km and rising") == ""  # decimal point is not a stop


def test_briefing_trims_a_truncated_response(monkeypatch) -> None:
    text = "Two leads were reviewed. One sits near a protected area. The third lead is"
    monkeypatch.setattr(briefing, "get_client", lambda: FakeGroq(reply(text, finish="length")))
    result = asyncio.run(briefing.briefing([_event()]))
    assert result.briefing == "Two leads were reviewed. One sits near a protected area."


def test_briefing_falls_back_when_truncated_before_any_sentence(monkeypatch) -> None:
    # The original field failure: only a date fragment arrived.
    monkeypatch.setattr(
        briefing, "get_client", lambda: FakeGroq(reply("For June 22, 2026", finish="length"))
    )
    result = asyncio.run(briefing.briefing([_event()]))
    assert "OceanGuard is tracking" in result.briefing


def test_briefing_keeps_a_complete_response_untouched(monkeypatch) -> None:
    text = "All good. Nothing urgent."
    monkeypatch.setattr(briefing, "get_client", lambda: FakeGroq(reply(text)))
    assert asyncio.run(briefing.briefing([_event()])).briefing == text


def test_ask_trims_a_truncated_answer(monkeypatch) -> None:
    text = "There are 3 leads. The top one is near an MPA. Next you could"
    monkeypatch.setattr(ask, "get_client", lambda: FakeGroq(reply(text, finish="length")))
    result = asyncio.run(ask.ask("what is going on?"))
    assert result.answer == "There are 3 leads. The top one is near an MPA."


def test_strip_markdown_normalises_hyphens_and_can_keep_bullets() -> None:
    from app.agents.helpers import strip_markdown

    text = "**bar‑reef‑003** is highest.\n- first\n- second"
    assert strip_markdown(text) == "bar-reef-003 is highest.\nfirst\nsecond"
    assert strip_markdown(text, keep_bullets=True) == "bar-reef-003 is highest.\n- first\n- second"
