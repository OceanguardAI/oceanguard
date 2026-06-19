"""In-memory store for risk events."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock

from app.core.config import settings
from app.models.schemas import RiskEvent, RiskSummary


class RiskEventRepository:
    def __init__(self) -> None:
        self._events: dict[str, RiskEvent] = {}
        self._path: Path | None = None
        self._lock = RLock()

    def load(self) -> None:
        path = settings.data_dir / "risk_events.json"
        if not path.exists():
            raise FileNotFoundError(
                f"risk_events.json not found at {path}. "
                "Generate it in ml/ and copy it into backend/data/."
            )

        raw = json.loads(path.read_text(encoding="utf-8"))
        self._path = path
        self._events = {item["id"]: RiskEvent(**item) for item in raw}

    def save(self) -> None:
        with self._lock:
            if self._path is None:
                self._path = settings.data_dir / "risk_events.json"
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = [event.model_dump() for event in self._events.values()]

            fd, tmp_path = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_path, self._path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise

    def replace_all(self, events: list[RiskEvent], *, persist: bool = True) -> int:
        """Replace the entire store with a fresh set of events (e.g. from a live feed)."""
        with self._lock:
            self._events = {event.id: event for event in events}
            if persist:
                self.save()
            return len(self._events)

    def upsert_many(self, events: list[RiskEvent], *, persist: bool = True) -> int:
        """Insert or update events by id, keeping existing events from other sources."""
        with self._lock:
            for event in events:
                self._events[event.id] = event
            if persist:
                self.save()
            return len(self._events)

    def all(
        self,
        source: str | None = None,
        level: str | None = None,
        review_status: str | None = None,
        near_mpa: bool | None = None,
    ) -> list[RiskEvent]:
        events = list(self._events.values())
        if source:
            events = [event for event in events if event.source == source]
        if level:
            events = [event for event in events if event.risk_level == level]
        if review_status:
            events = [event for event in events if event.review_status == review_status]
        if near_mpa is True:
            events = [event for event in events if event.near_mpa or event.inside_mpa]
        return events

    def get(self, event_id: str) -> RiskEvent | None:
        return self._events.get(event_id)

    def update_review(self, event_id: str, status: str) -> RiskEvent | None:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None

            updated = event.model_copy(update={"review_status": status})
            self._events[event_id] = updated
            self.save()
            return updated

    def summary(self) -> RiskSummary:
        events = list(self._events.values())
        source_counts: dict[str, int] = {}
        risk_level_counts: dict[str, int] = {}
        review_status_counts: dict[str, int] = {}

        for event in events:
            source_counts[event.source] = source_counts.get(event.source, 0) + 1
            risk_level_counts[event.risk_level] = risk_level_counts.get(event.risk_level, 0) + 1
            review_status_counts[event.review_status] = (
                review_status_counts.get(event.review_status, 0) + 1
            )

        highest = max(events, key=lambda item: item.risk_score, default=None)
        return RiskSummary(
            total_events=len(events),
            source_counts=source_counts,
            risk_level_counts=risk_level_counts,
            review_status_counts=review_status_counts,
            inside_mpa_count=sum(1 for event in events if event.inside_mpa),
            near_mpa_count=sum(1 for event in events if event.near_mpa),
            highest_risk_event_id=highest.id if highest else None,
            highest_risk_score=highest.risk_score if highest else None,
        )


repo = RiskEventRepository()
