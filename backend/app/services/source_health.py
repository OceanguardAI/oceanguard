"""Safe, provider-neutral source health reporting."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.services import ais_stream, gfw_ingest, sentinel_sar
from app.store.activity import activity_store


def _configured_state(configured: bool) -> str:
    return "configured" if configured else "not_configured"


def get_source_health() -> dict[str, Any]:
    """Return source readiness without exposing tokens or inventing liveness."""
    activity = activity_store.status()
    gfw_configured = gfw_ingest.ingestion_enabled()
    ais_configured = ais_stream.ais_enabled()
    sentinel_configured = sentinel_sar.is_configured()
    yolo_configured = bool(settings.yolo_service_url)

    return {
        "generated_at": datetime.now(timezone.utc),
        "region_bbox": settings.gfw_region_bbox,
        "sources": [
            {
                "id": "gfw_4wings",
                "kind": "satellite_activity",
                "configured": gfw_configured,
                "state": _configured_state(gfw_configured),
                "last_attempt_at": activity.get("last_attempt_at"),
                "last_success_at": activity.get("last_success_at"),
                "error_category": activity.get("error_category"),
                "data_state": (
                    "stale" if activity.get("error_category")
                    else "available" if activity.get("aggregate_count", 0)
                    else "empty"
                ),
                "limitation": "4Wings rows are activity aggregates, not vessel identities.",
            },
            {
                "id": "aisstream",
                "kind": "live_ais_sample",
                "configured": ais_configured,
                "state": _configured_state(ais_configured),
                "last_attempt_at": None,
                "last_success_at": None,
                "error_category": None,
                "data_state": "sample_only" if ais_configured else "unavailable",
                "limitation": "A short stream sample cannot prove absence or intentional AIS disablement.",
            },
            {
                "id": "sentinel_hub",
                "kind": "sar_imagery",
                "configured": sentinel_configured,
                "state": _configured_state(sentinel_configured),
                "last_attempt_at": None,
                "last_success_at": None,
                "error_category": None,
                "data_state": "on_demand" if sentinel_configured else "unavailable",
                "limitation": "The current Process API response does not provide scene identity metadata.",
            },
            {
                "id": "yolo_service",
                "kind": "sar_inference",
                "configured": yolo_configured,
                "state": _configured_state(yolo_configured),
                "last_attempt_at": None,
                "last_success_at": None,
                "error_category": None,
                "data_state": "on_demand" if yolo_configured else "unavailable",
                "limitation": "A model contact is an observation candidate until scene metadata is confirmed.",
            },
        ],
    }
