"""Narrator agent: explain why a single vessel was flagged."""
from __future__ import annotations
from app.agents.client import get_client
from app.models.schemas import RiskEvent, NarrateResponse


SYSTEM_PROMPT = """You are a marine conservation analyst for OceanGuard AI.
Your role is to explain SAR vessel detections clearly for patrol officers.
Always use hedged language — say "may indicate", "suggests", "could be".
Never make accusations. Never identify individuals. Decisions are made by officers, not you.
Be factual, concise, and use 2-3 sentences per section."""


def _build_user_prompt(event: RiskEvent) -> str:
    lines = [
        f"Detection ID: {event.id}",
        f"Source: {event.source}",
        f"Location: {event.lat:.5f}N, {event.lon:.5f}E",
        f"Risk Score: {event.risk_score} ({event.risk_level})",
        f"SAR Confidence: {event.sar_confidence:.0%}",
        f"AIS Matched: {'Yes' if event.ais_matched else 'No'} "
        f"(AIS Data Available: {'Yes' if event.ais_data_available else 'No'})",
        f"Inside MPA: {'Yes' if event.inside_mpa else 'No'}",
        f"Near MPA (<=5km): {'Yes' if event.near_mpa else 'No'}",
        f"MPA Name: {event.mpa_name or 'N/A'}",
        f"Distance to MPA: {event.distance_to_mpa_km} km" if event.distance_to_mpa_km is not None else "Distance to MPA: N/A",
        f"Distance to Port: {event.distance_from_port_km} km" if event.distance_from_port_km is not None else "Distance to Port: N/A",
        f"Matching Method: {event.matching_method}",
        "",
        "In 2-3 sentences each:",
        "1. why_flagged: Why was this vessel flagged? Mention the key risk factors.",
        "2. uncertainty: What makes this uncertain? What could explain it innocently?",
        "",
        'Return as JSON: {"why_flagged": "...", "uncertainty": "..."}',
    ]
    return "\n".join(lines)


def _fallback(event: RiskEvent) -> NarrateResponse:
    dist_str = (
        f"{event.distance_to_mpa_km:.1f} km from {event.mpa_name}"
        if event.distance_to_mpa_km is not None and event.mpa_name
        else "in the monitored area"
    )
    ais_str = (
        "no matching AIS broadcast was found within the 2 km / 3-hour window"
        if event.ais_data_available
        else "AIS coverage was not available in this area"
    )

    why = (
        f"Vessel detected at {event.lat:.4f}N {event.lon:.4f}E at "
        f"{event.sar_confidence:.0%} SAR confidence. The detection is {dist_str} "
        f"and {ais_str}. Risk score: {event.risk_score:.2f} ({event.risk_level})."
    )
    uncertainty = (
        f"SAR-only detection ({event.sar_confidence:.0%} confidence) without confirmed AIS match. "
        "The vessel may be in transit, anchored legally, or using a different AIS identifier. "
        "A conservation officer should cross-reference with vessel tracking systems before any action."
    )
    return NarrateResponse(why_flagged=why, uncertainty=uncertainty)


async def narrate(event: RiskEvent) -> NarrateResponse:
    client = get_client()
    if client is None:
        return _fallback(event)

    try:
        import json as _json
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(event)}],
        )
        text = message.content[0].text.strip()
        if "{" in text:
            start = text.index("{")
            end   = text.rindex("}") + 1
            parsed = _json.loads(text[start:end])
            return NarrateResponse(
                why_flagged=parsed.get("why_flagged", ""),
                uncertainty=parsed.get("uncertainty", ""),
            )
        return NarrateResponse(why_flagged=text, uncertainty="")
    except Exception as e:
        print(f"Narrator agent error: {e}")
        return _fallback(event)
