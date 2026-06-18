"""Sentinel-1 SAR image chip endpoint."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services import sentinel_sar

router = APIRouter()


@router.get("/sar-image/status")
def sar_status() -> dict[str, bool]:
    """Report whether Sentinel Hub SAR imagery is configured."""
    return {"configured": sentinel_sar.is_configured()}


@router.get("/sar-image")
def sar_image(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    date: str | None = Query(None, description="ISO date the chip should end at."),
) -> Response:
    """Return a Sentinel-1 VV SAR chip (PNG) centred on the detection."""
    if not sentinel_sar.is_configured():
        raise HTTPException(
            status_code=503,
            detail="SAR imagery is not configured. Add SENTINELHUB_CLIENT_ID and "
            "SENTINELHUB_CLIENT_SECRET.",
        )
    try:
        png = sentinel_sar.fetch_chip(lat, lon, date)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Sentinel Hub error: {exc.response.status_code}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Sentinel Hub request failed: {exc}")
    # Cache chips at the edge for a day; detections don't change retroactively.
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
