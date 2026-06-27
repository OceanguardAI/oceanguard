"""Narrator agent: explain why one vessel was flagged."""
from __future__ import annotations

from app.agents.client import get_client
from app.agents.helpers import (
    event_summary_line,
    extract_json_object,
    extract_text,
    strip_markdown,
)
from app.core.config import settings
from app.models.schemas import NarrateResponse, RiskEvent

SYSTEM_PROMPT = """You are a marine conservation analyst for OceanGuard AI.
Explain SAR vessel detections clearly for patrol officers.
Always use cautious language such as may, could, or suggests.
Never accuse anyone or imply certainty. Human officers make decisions.

Formatting rules (important):
- The "why_flagged" and "uncertainty" values must be plain text only.
- Do NOT use Markdown: no asterisks (* or **), no bold, no headings (#),
  no backticks, no bullet characters, no underscores for emphasis.
- Each value is 1 to 3 complete sentences of flowing prose."""


def _build_user_prompt(event: RiskEvent) -> str:
    return "\n".join(
        [
            "Explain this detection for a conservation officer.",
            f"Event summary: {event_summary_line(event, include_review=True)}",
            f"SAR confidence: {event.sar_confidence:.0%}",
            f"AIS matched: {event.ais_matched}",
            f"AIS data available: {event.ais_data_available}",
            f"Inside MPA: {event.inside_mpa}",
            f"Near MPA: {event.near_mpa}",
            f"MPA name: {event.mpa_name or 'N/A'}",
            f"Distance to MPA km: {event.distance_to_mpa_km}",
            f"Distance to port km: {event.distance_from_port_km}",
            f"Recommended action: {event.recommended_action}",
            f"Current review status: {event.review_status}",
            'Return JSON: {"why_flagged":"...","uncertainty":"..."}',
        ]
    )


def _fallback(event: RiskEvent) -> NarrateResponse:
    location_context = (
        f"{event.distance_to_mpa_km:.1f} km from {event.mpa_name}"
        if event.distance_to_mpa_km is not None and event.mpa_name
        else "outside the Bar Reef proximity workflow"
    )
    ais_context = (
        "no matching AIS broadcast was found in the configured time and distance window"
        if event.ais_data_available and not event.ais_matched
        else "AIS coverage was unavailable for this scene"
        if not event.ais_data_available
        else "an AIS match was present"
    )
    why_flagged = (
        f"This detection was flagged because SAR identified a vessel-like object with "
        f"{event.sar_confidence:.0%} confidence and the event sits {location_context}. "
        f"In this case, {ais_context}, which increases review priority to "
        f"{event.risk_level} at score {event.risk_score:.2f}."
    )
    uncertainty = (
        "This remains a decision-support lead rather than proof of wrongdoing. "
        "SAR confidence is imperfect, AIS gaps can happen for benign reasons, and "
        "a human reviewer should cross-check scene context before any patrol action."
    )
    return NarrateResponse(why_flagged=why_flagged, uncertainty=uncertainty)


async def narrate(event: RiskEvent) -> NarrateResponse:
    client = get_client()
    if client is None:
        return _fallback(event)

    try:
        from google.genai import types

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=_build_user_prompt(event),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=settings.agent_narrator_max_tokens,
                response_mime_type="application/json",
            ),
        )
        text = extract_text(response)
        payload = extract_json_object(text)
        response = NarrateResponse(
            why_flagged=strip_markdown(payload.get("why_flagged", "")),
            uncertainty=strip_markdown(payload.get("uncertainty", "")),
        )
        if not response.why_flagged or not response.uncertainty:
            return _fallback(event)
        return response
    except Exception:
        return _fallback(event)
