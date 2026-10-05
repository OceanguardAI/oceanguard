"""The chatbot's description of scoring must match the data it is describing.

Scored case records come from the weighted formula in ml/pipeline/risk.py. The
live GFW feed produces unscored activity cells. These tests keep the hand-written
agent knowledge from drifting away from that reality again.
"""
from __future__ import annotations

import json

from app.agents import ask
from app.core.config import settings

# Thresholds stated in the agent knowledge text.
_THRESHOLDS = (("CRITICAL", 0.75), ("HIGH", 0.55), ("MEDIUM", 0.35))


def _level(score: float) -> str:
    for level, floor in _THRESHOLDS:
        if score >= floor:
            return level
    return "LOW"


def test_documented_thresholds_reproduce_every_seed_event_level() -> None:
    events = json.loads((settings.data_dir / "risk_events.json").read_text(encoding="utf-8"))
    assert events, "seed events missing"
    mismatches = [e["id"] for e in events if _level(e["risk_score"]) != e["risk_level"]]
    assert mismatches == []


def test_system_knowledge_states_the_documented_thresholds() -> None:
    for level, floor in _THRESHOLDS:
        assert f"{level} >= {floor:.2f}" in ask.SYSTEM_KNOWLEDGE


def test_fallback_methodology_matches_documented_thresholds() -> None:
    answer = ask._methodology_answer("how is the risk score calculated").answer
    for level, floor in _THRESHOLDS:
        assert f"{level} >= {floor:.2f}" in answer
    assert "0.80" not in answer  # retired additive-formula threshold


def test_agent_knowledge_does_not_score_live_activity_cells() -> None:
    assert "unscored" in ask.SYSTEM_KNOWLEDGE
    assert "SAMPLE" in ask.SYSTEM_KNOWLEDGE
    assert "0.25 baseline" not in ask.SYSTEM_KNOWLEDGE
