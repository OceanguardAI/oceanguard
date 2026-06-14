"""In-memory store for risk events. Loaded once on startup."""
from __future__ import annotations
import json
from pathlib import Path
from app.models.schemas import RiskEvent
from app.core.config import settings


class RiskEventRepository:
    def __init__(self) -> None:
        self._events: dict[str, RiskEvent] = {}

    def load(self) -> None:
        """Load risk_events.json into memory."""
        path = settings.data_dir / "risk_events.json"
        if not path.exists():
            raise FileNotFoundError(
                f"risk_events.json not found at {path}. "
                "Run ml/build_risk_events.py first and copy to backend/data/."
            )
        raw: list[dict] = json.loads(path.read_text())
        self._events = {item["id"]: RiskEvent(**item) for item in raw}
        print(f"Loaded {len(self._events)} risk events from {path}")

    def all(
        self,
        source: str | None = None,
        level: str | None = None,
    ) -> list[RiskEvent]:
        events = list(self._events.values())
        if source:
            events = [e for e in events if e.source == source]
        if level:
            events = [e for e in events if e.risk_level == level]
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


# Module-level singleton — imported by routes
repo = RiskEventRepository()
