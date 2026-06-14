"""Patrol agent: rank events for patrol priority."""
from __future__ import annotations
from app.agents.client import get_client
from app.models.schemas import RiskEvent, PatrolItem


SYSTEM_PROMPT = """You are a patrol planning assistant for marine conservation.
Rank the provided vessel detections from highest to lowest patrol priority.
Priority order: (1) inside MPA, (2) near MPA <=5km, (3) highest risk score.
Return a JSON array of objects: [{id, rank, risk_level, distance_to_mpa_km, justification}].
Justification: 1-2 sentences. Never make accusations. Officers decide."""


def _deterministic_rank(events: list[RiskEvent]) -> list[PatrolItem]:
    """Fallback: deterministic sort + template justifications."""
    def sort_key(e: RiskEvent):
        return (-int(e.inside_mpa), -int(e.near_mpa), -e.risk_score)

    sorted_events = sorted(events, key=sort_key)
    items = []
    for rank, event in enumerate(sorted_events, start=1):
        if event.inside_mpa:
            just = f"Vessel is inside {event.mpa_name} — highest priority for investigation."
        elif event.near_mpa:
            just = (
                f"Vessel is {event.distance_to_mpa_km:.1f} km from {event.mpa_name} "
                f"with no AIS match. Score {event.risk_score:.2f} ({event.risk_level})."
            )
        else:
            if event.distance_to_mpa_km is not None:
                just = (
                    f"Dark vessel detected {event.distance_to_mpa_km:.1f} km from monitored MPA. "
                    f"Risk score {event.risk_score:.2f} ({event.risk_level}). Routine verification recommended."
                )
            else:
                just = f"Dark vessel detected in monitored zone. Score {event.risk_score:.2f} ({event.risk_level})."

        items.append(PatrolItem(
            id=event.id,
            rank=rank,
            risk_level=event.risk_level,
            distance_to_mpa_km=event.distance_to_mpa_km,
            justification=just,
        ))
    return items


async def patrol(events: list[RiskEvent]) -> list[PatrolItem]:
    client = get_client()
    if client is None or not events:
        return _deterministic_rank(events)

    prompt = "Rank these detections for patrol priority:\n\n"
    for e in events:
        prompt += (
            f"- {e.id}: level={e.risk_level}, score={e.risk_score}, "
            f"inside_mpa={e.inside_mpa}, near_mpa={e.near_mpa}, "
            f"dist_km={e.distance_to_mpa_km}\n"
        )
    prompt += "\nReturn JSON array only."

    try:
        import json as _json
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        if "[" in text:
            start = text.index("[")
            end   = text.rindex("]") + 1
            parsed = _json.loads(text[start:end])
            return [PatrolItem(**item) for item in parsed]
        return _deterministic_rank(events)
    except Exception as e:
        print(f"Patrol agent error: {e}")
        return _deterministic_rank(events)
