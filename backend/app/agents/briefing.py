"""Briefing agent for daily summaries."""
from __future__ import annotations

from datetime import datetime, timezone

from app.agents.client import get_client
from app.agents.helpers import alertness_level, build_event_context, extract_text
from app.core.config import settings
from app.models.schemas import BriefingResponse, RiskEvent

SYSTEM_PROMPT = """You are a senior marine conservation analyst.
Write a concise daily briefing for conservation officers.
Stay factual, hedge uncertainty, and never make accusations.

Formatting rules (important):
- Write in plain prose only. Do NOT use Markdown: no asterisks (* or **),
  no headings (#), no bullet characters, no bold markers.
- Do NOT use placeholder text such as [Insert Date] or [Location]. You are
  given the real date and figures; use them directly.
- Write exactly 3 complete, finished sentences. Every sentence must end with a period.
- Never stop mid-sentence. If you are running out of space, shorten your sentences.
- Do not list individual vessel IDs. Summarise counts, risk levels, and MPA context only."""


def _build_user_prompt(events: list[RiskEvent]) -> str:
    priority_count = sum(1 for event in events if event.risk_level in {"HIGH", "CRITICAL"})
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    return "\n".join(
        [
            f"Today's date is {today}. Summarise these detections for a patrol briefing.",
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
        from google.genai import types

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=_build_user_prompt(events),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=settings.agent_briefing_max_tokens,
            ),
        )
        text = extract_text(response)
        if not text:
            return _fallback(events)
        return BriefingResponse(briefing=text)
    except Exception:
        return _fallback(events)
