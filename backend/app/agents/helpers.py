"""Shared helpers for agent parsing and fallback behavior."""
from __future__ import annotations

import json
from typing import Any

from app.models.schemas import RiskEvent


def first_text_block(content: list[Any]) -> str:
    """Return the first non-empty text block from an Anthropic response."""
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object embedded in a text response."""
    start = text.index("{")
    end = text.rindex("}") + 1
    payload = json.loads(text[start:end])
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    return payload


def extract_json_array(text: str) -> list[dict[str, Any]]:
    """Extract the first JSON array embedded in a text response."""
    start = text.index("[")
    end = text.rindex("]") + 1
    payload = json.loads(text[start:end])
    if not isinstance(payload, list):
        raise ValueError("Expected a JSON array.")
    return payload


def alertness_level(events: list[RiskEvent]) -> str:
    """Return a simple patrol alertness label from current event severities."""
    if any(event.risk_level == "CRITICAL" for event in events):
        return "HIGH"
    if any(event.risk_level == "HIGH" for event in events):
        return "HIGH"
    if events:
        return "ELEVATED"
    return "LOW"
