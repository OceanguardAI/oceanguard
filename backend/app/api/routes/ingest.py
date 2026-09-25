"""GFW activity reporting and external event ingestion endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.models.schemas import ActivityPage, RiskEvent
from app.services import gfw_ingest
from app.store.activity import activity_store
from app.store.repository import repo

router = APIRouter()


@router.get("/ingest/status")
def ingest_status() -> dict[str, object]:
    return {
        "live_source": "Global Fishing Watch 4Wings SAR presence report",
        "gfw_token_configured": gfw_ingest.ingestion_enabled(),
        "region_bbox": settings.gfw_region_bbox,
        "lookback_days": settings.gfw_lookback_days,
        "activity": activity_store.status(),
        "risk_events_mode": repo.mode,
    }


@router.get("/activity/gfw", response_model=ActivityPage)
def get_gfw_activity(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=600, ge=1, le=1000),
    bbox: str | None = Query(default=None, description="west,south,east,north"),
) -> ActivityPage:
    bounds = None
    if bbox:
        try:
            values = tuple(float(part) for part in bbox.split(","))
            if len(values) != 4 or values[0] >= values[2] or values[1] >= values[3]:
                raise ValueError
            bounds = values
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="bbox must be west,south,east,north") from exc
    return activity_store.page(offset=offset, limit=limit, bbox=bounds)


@router.post("/ingest/gfw")
def ingest_gfw() -> dict[str, object]:
    if not gfw_ingest.ingestion_enabled():
        raise HTTPException(
            status_code=400,
            detail="GFW_API_TOKEN is not configured. Add it to backend/.env to enable live ingestion.",
        )
    try:
        activity = gfw_ingest.fetch_activity()
    except Exception as exc:  # network / auth / parse failures
        activity_store.failure(exc)
        raise HTTPException(
            status_code=502,
            detail=f"GFW report failed: {activity_store.status()['error_category']}",
        ) from exc

    count = activity_store.replace(activity)
    return {
        "aggregate_cells": count,
        "source": "Global Fishing Watch 4Wings SAR presence report",
        "record_type": "activity_aggregate",
    }


@router.post("/ingest/push")
def ingest_push(events: list[RiskEvent], mode: str = "merge") -> dict[str, object]:
    """Receive externally-computed events (e.g. live YOLO/Sentinel-1 job).

    mode=merge upserts by id (keeps other sources); mode=replace swaps the store.
    """
    if mode not in {"merge", "replace"}:
        raise HTTPException(status_code=400, detail="mode must be 'merge' or 'replace'.")
    if mode == "replace":
        total = repo.replace_all(events)
    else:
        total = repo.upsert_many(events)
    return {"received": len(events), "total_events": total, "mode": mode}
