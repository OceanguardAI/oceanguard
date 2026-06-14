"""Briefing agent: daily situation summary for conservation officers."""
from __future__ import annotations
from app.agents.client import get_client
from app.models.schemas import RiskEvent, BriefingResponse


SYSTEM_PROMPT = """You are a senior marine conservation analyst.
Write a concise daily briefing for conservation officers.
Mention the highest-risk detection by name. Recommend an alertness level (LOW/ELEVATED/HIGH).
Use 3-5 sentences. Never make accusations. Decisions rest with human officers."""


def _build_user_prompt(events: list[RiskEvent]) -> str:
    lines = ["Summarise the following dark vessel detections for a daily briefing:", ""]
    for e in sorted(events, key=lambda x: x.risk_score, reverse=True):
        lines.append(
            f"- {e.id}: {e.risk_level} ({e.risk_score:.2f}), "
            f"{e.distance_to_mpa_km or 'N/A'} km from {e.mpa_name or 'MPA'}, "
            f"near_mpa={e.near_mpa}"
        )
    return "\n".join(lines)


def _fallback(events: list[RiskEvent]) -> BriefingResponse:
    if not events:
        return BriefingResponse(
            briefing="No dark vessel detections recorded. Continue routine monitoring."
        )
    top = max(events, key=lambda e: e.risk_score)
    high = [e for e in events if e.risk_level in ("HIGH", "CRITICAL")]
    briefing = (
        f"Monitoring update: {len(events)} SAR dark-vessel detections recorded near Bar Reef Marine Sanctuary. "
        f"Highest-risk detection is {top.id} (score {top.risk_score:.2f} / {top.risk_level}) "
        f"at {top.distance_to_mpa_km:.1f} km from {top.mpa_name}. "
        f"{len(high)} detection(s) rated HIGH or CRITICAL. "
        f"Alertness level: {'HIGH' if high else 'ELEVATED'}. "
        "All findings require human verification before any response."
    )
    return BriefingResponse(briefing=briefing)


async def briefing(events: list[RiskEvent]) -> BriefingResponse:
    client = get_client()
    if client is None or not events:
        return _fallback(events)

    try:
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(events)}],
        )
        return BriefingResponse(briefing=message.content[0].text.strip())
    except Exception as e:
        print(f"Briefing agent error: {e}")
        return _fallback(events)
