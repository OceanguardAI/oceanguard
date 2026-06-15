"""Patrol prioritization agent."""
from __future__ import annotations

import json

from app.agents.client import get_client
from app.models.schemas import PatrolItem, RiskEvent

SYSTEM_PROMPT = """You are a patrol planning assistant for marine conservation officers.
Rank detections by patrol priority using risk score and MPA proximity.
Be cautious, factual, and avoid any accusatory framing."""


def _deterministic_rank(events: list[RiskEvent]) -> list[PatrolItem]:
    ranked = sorted(
        events,
        key=lambda event: (
            event.risk_score,
            event.inside_mpa,
            event.near_mpa,
            -(event.distance_to_mpa_km or 9999),
        ),
        reverse=True,
    )

    items: list[PatrolItem] = []
    for rank, event in enumerate(ranked, start=1):
        justification = (
            f"Ranked #{rank} because it has score {event.risk_score:.2f} "
            f"and risk level {event.risk_level}"
        )
        if event.inside_mpa:
            justification += ", and it falls inside the protected area."
        elif event.near_mpa:
            justification += ", and it is close to the protected-area boundary."
        else:
            justification += "."

        items.append(
            PatrolItem(
                id=event.id,
                rank=rank,
                risk_level=event.risk_level,
                distance_to_mpa_km=event.distance_to_mpa_km,
                justification=justification,
            )
        )
    return items


async def patrol(events: list[RiskEvent]) -> list[PatrolItem]:
    client = get_client()
    if client is None or not events:
        return _deterministic_rank(events)

    prompt_lines = ["Rank these detections for patrol priority and return JSON array only:"]
    for event in events:
        prompt_lines.append(
            f"- {event.id}: score={event.risk_score}, level={event.risk_level}, "
            f"inside_mpa={event.inside_mpa}, near_mpa={event.near_mpa}, "
            f"distance_to_mpa_km={event.distance_to_mpa_km}"
        )

    try:
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "\n".join(prompt_lines)}],
        )
        text = message.content[0].text.strip()
        start = text.index("[")
        end = text.rindex("]") + 1
        payload = json.loads(text[start:end])
        return [PatrolItem(**item) for item in payload]
    except Exception:
        return _deterministic_rank(events)
