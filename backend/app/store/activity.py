"""Process-local activity snapshot and source state until durable storage lands."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock

import httpx

from app.models.schemas import ActivityAggregate, ActivityPage


class ActivityStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._items: list[ActivityAggregate] = []
        self._attempted_at: datetime | None = None
        self._succeeded_at: datetime | None = None
        self._error_category: str | None = None

    def replace(self, items: list[ActivityAggregate]) -> int:
        with self._lock:
            self._items = list(items)
            self._attempted_at = datetime.now(timezone.utc)
            self._succeeded_at = self._attempted_at
            self._error_category = None
            return len(self._items)

    def failure(self, error: Exception) -> None:
        category = "provider_error"
        if isinstance(error, httpx.HTTPStatusError):
            code = error.response.status_code
            category = (
                "unauthorized" if code in (401, 403) else
                "quota_limited" if code == 429 else
                "provider_unavailable" if code >= 500 else "provider_error"
            )
        elif isinstance(error, httpx.TimeoutException):
            category = "timeout"
        elif isinstance(error, (ValueError, TypeError)):
            category = "invalid_response"
        with self._lock:
            self._attempted_at = datetime.now(timezone.utc)
            self._error_category = category

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "scope": "process_local",
                "last_attempt_at": self._attempted_at,
                "last_success_at": self._succeeded_at,
                "error_category": self._error_category,
                "aggregate_count": len(self._items),
            }

    def page(
        self,
        *,
        offset: int = 0,
        limit: int = 600,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> ActivityPage:
        with self._lock:
            items = self._items
            if bbox:
                west, south, east, north = bbox
                items = [a for a in items if west <= a.lon <= east and south <= a.lat <= north]
            total = len(items)
            state = "not_loaded" if self._succeeded_at is None else "available" if self._items else "empty"
            if self._succeeded_at and (
                self._error_category or datetime.now(timezone.utc) - self._succeeded_at > timedelta(hours=24)
            ):
                state = "stale"
            return ActivityPage(
                items=items[offset:offset + limit],
                total=total,
                offset=offset,
                limit=limit,
                data_state=state,
            )


activity_store = ActivityStore()
