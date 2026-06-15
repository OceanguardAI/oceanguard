"""In-memory store for risk events."""
from __future__ import annotations

import json

from app.core.config import settings
from app.models.schemas import RiskEvent


class RiskEventRepository:
    def __init__(self) -> None:
        self._events: dict[str, RiskEvent] = {}

    def load(self) -> None:
        path = settings.data_dir / "risk_events.json"
        if not path.exists():
            raise FileNotFoundError(
                f"risk_events.json not found at {path}. "
                "Generate it in ml/ and copy it into backend/data/."
            )

        raw = json.loads(path.read_text(encoding="utf-8"))
        self._events = {item["id"]: RiskEvent(**item) for item in raw}

    def all(self, source: str | None = None, level: str | None = None) -> list[RiskEvent]:
        events = list(self._events.values())
        if source:
            events = [event for event in events if event.source == source]
        if level:
            events = [event for event in events if event.risk_level == level]
        return events

    def get(self, event_id: str) -> RiskEvent | None:
        return self._events.get(event_id)

    def update_review(self, event_id: str, status: str) -> RiskEvent | None:
        event = self._events.get(event_id)
        if event is None:
            return None

        updated = event.model_copy(update={"review_status": status})
        self._events[event_id] = updated
        return updated


repo = RiskEventRepository()
