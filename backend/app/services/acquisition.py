"""Shared validation and provenance helpers for satellite requests."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def parse_request_time(value: str) -> datetime:
    """Parse an ISO timestamp and normalize it to UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("date must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def provenance(*, lat: float, lon: float, requested_at: datetime, result: dict[str, Any]) -> dict[str, Any]:
    """Describe what a provider response proves without guessing scene facts."""
    acquisition_id = result.get("acquisition_id") or result.get("scene_id")
    observed_at = result.get("acquisition_time") or result.get("scene_time")
    complete = bool(acquisition_id and observed_at)
    return {
        "provider": "Sentinel-1 SAR via YOLO inference service",
        "requested_center": {"lat": lat, "lon": lon},
        "requested_at": requested_at.isoformat().replace("+00:00", "Z"),
        "acquisition_id": acquisition_id,
        "observed_at": observed_at,
        "coverage_status": "scene_metadata_available" if complete else "scene_time_unverified",
        "identity_claim": "observation_candidate_only",
    }
