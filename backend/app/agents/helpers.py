"""Shared helpers for agent parsing and fallback behavior."""
from __future__ import annotations

import json
import re
from typing import Any

from app.models.schemas import RiskEvent


def strip_markdown(text: str) -> str:
    """Reduce model Markdown to plain prose.

    The agents are prompted for plain text, but models occasionally emit
    emphasis or bullet markers anyway. Several frontend surfaces (the evidence
    card, the patrol board) render these strings raw, so literal ``**`` would
    show on screen. This is the source-side safety net for those fields.
    """
    if not text:
        return text
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)      # **bold**
    text = re.sub(r"__(.*?)__", r"\1", text)            # __bold__
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)      # # headings
    text = re.sub(r"(?m)^\s*[-*•]\s+", "", text)        # leading bullet markers
    text = re.sub(r"[*_`]+", "", text)                   # stray emphasis chars
    text = re.sub(r"\n{3,}", "\n\n", text)              # collapse blank runs
    return text.strip()


_SENTENCE_END = re.compile(r"[.!?][\"')\]]*(?=\s|$)")


def trim_to_last_sentence(text: str) -> str:
    """Drop a trailing partial sentence; return '' if no sentence is complete."""
    matches = list(_SENTENCE_END.finditer(text))
    if not matches:
        return ""
    return text[: matches[-1].end()].strip()


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


def event_summary_line(event: RiskEvent, include_review: bool = False) -> str:
    """Return a compact single-line summary of a risk event."""
    segments = [
        f"{event.id}",
        f"source={event.source}",
        f"risk={event.risk_level} ({event.risk_score:.2f})",
        f"ais_matched={event.ais_matched}",
        f"inside_mpa={event.inside_mpa}",
        f"near_mpa={event.near_mpa}",
        f"distance_to_mpa_km={event.distance_to_mpa_km}",
        f"nearest_port={event.nearest_port}",
        f"timestamp={event.timestamp}",
    ]
    if include_review:
        segments.append(f"review_status={event.review_status}")
    return ", ".join(segments)


def build_event_context(
    events: list[RiskEvent],
    *,
    limit: int = 10,
    include_review: bool = False,
) -> str:
    """Return a multi-line event context block sorted by descending risk score."""
    selected = sorted(events, key=lambda item: item.risk_score, reverse=True)[: max(limit, 0)]
    if not selected:
        return "No events available."
    return "\n".join(f"- {event_summary_line(event, include_review=include_review)}" for event in selected)
