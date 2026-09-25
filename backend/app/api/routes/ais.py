"""Endpoints for real-time AIS (AISStream.io) over the monitored region."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.services import ais_stream
from app.store.repository import repo

router = APIRouter()


@router.get("/ais/status")
def ais_status() -> dict[str, object]:
    return {
        "live_source": "AISStream.io",
        "ais_key_configured": ais_stream.ais_enabled(),
        "region_bbox": settings.gfw_region_bbox,
    }


@router.get("/ais/live")
async def ais_live(seconds: int = Query(default=20, ge=5, le=60)) -> dict[str, object]:
    """Sample live AIS positions over the monitored bbox for `seconds`."""
    if not ais_stream.ais_enabled():
        raise HTTPException(
            status_code=400,
            detail="AISSTREAM_API_KEY is not configured. Add it to backend/.env.",
        )
    try:
        vessels = await ais_stream.collect_ais(seconds=seconds)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AIS sampling failed: {exc}") from exc
    return {"sampled_seconds": seconds, "vessel_count": len(vessels), "vessels": vessels}


@router.post("/ais/verify-dark")
async def verify_dark(seconds: int = Query(default=20, ge=5, le=60)) -> dict[str, object]:
    """Look for recent AIS candidates without treating a short sample as full coverage."""
    if not ais_stream.ais_enabled():
        raise HTTPException(status_code=400, detail="AISSTREAM_API_KEY is not configured.")
    try:
        vessels = await ais_stream.collect_ais(seconds=seconds)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AIS sampling failed: {exc}") from exc

    results = []
    for event in repo.all():
        if event.ais_matched:
            continue
        # GFW 4Wings rows are aggregate cells, not individual vessels.
        status, candidates = (
            ("unavailable", [])
            if event.source == "GFW"
            else ais_stream.sample_association(event.lat, event.lon, event.timestamp, vessels)
        )
        results.append({
            "id": event.id,
            "lat": event.lat,
            "lon": event.lon,
            "risk_level": event.risk_level,
            "association_status": status,
            "candidate_mmsi": candidates,
            "dark_confirmed": False,
        })
    return {
        "live_ais_vessels": len(vessels),
        "dark_candidates_checked": len(results),
        "dark_confirmed": 0,
        "sample_complete_for_absence": False,
        "results": results,
    }
