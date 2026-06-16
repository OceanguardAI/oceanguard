"""Briefing agent for daily summaries."""
from __future__ import annotations

from app.agents.client import get_client
from app.agents.helpers import alertness_level, build_event_context, first_text_block
from app.core.config import settings
from app.models.schemas import BriefingResponse, RiskEvent

SYSTEM_PROMPT = """You are a senior marine conservation analyst.
Write a concise daily briefing for conservation officers.
Stay factual, hedge uncertainty, and never make accusations."""


def _build_user_prompt(events: list[RiskEvent]) -> str:
    priority_count = sum(1 for event in events if event.risk_level in {"HIGH", "CRITICAL"})
    return "\n".join(
        [
            "Summarise these detections for a patrol briefing.",
            f"Total detections: {len(events)}",
            f"Recommended alertness baseline: {alertness_level(events)}",
            f"HIGH/CRITICAL detections: {priority_count}",
            "Top detections by risk:",
            build_event_context(events, limit=10, include_review=True),
        ]
    )


def _fallback(events: list[RiskEvent]) -> BriefingResponse:
    if not events:
        return BriefingResponse(briefing="No detections are loaded. Continue routine monitoring.")

    top = max(events, key=lambda event: event.risk_score)
    priority_count = sum(1 for event in events if event.risk_level in {"HIGH", "CRITICAL"})
    alertness = alertness_level(events)
    return BriefingResponse(
        briefing=(
            f"OceanGuard is tracking {len(events)} current detections in the store. "
            f"The highest-priority lead is {top.id} at score {top.risk_score:.2f} "
            f"({top.risk_level}), located {top.distance_to_mpa_km if top.distance_to_mpa_km is not None else 'outside MPA scoring'} km from the protected-area boundary. "
            f"There are {priority_count} HIGH or CRITICAL detections, so recommended alertness is {alertness}. "
            "All leads should be reviewed by an officer before any response."
        )
    )


async def briefing(events: list[RiskEvent]) -> BriefingResponse:
    client = get_client()
    if client is None or not events:
        return _fallback(events)

    try:
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(events)}],
        )
        text = first_text_block(message.content)
        if not text:
            return _fallback(events)
        return BriefingResponse(briefing=text)
    except Exception:
        return _fallback(events)
