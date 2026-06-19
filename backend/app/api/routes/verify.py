"""On-demand YOLO verification of a detection.

An officer reviewing a GFW detection can ask our own fine-tuned model to look at
the live Sentinel-1 radar for that exact point. This proxies to the separate
oceanguard-yolo service (kept apart so torch never bloats this API) and, when
the model confirms a vessel, records that two independent systems agree.

This is the answer to the dark-vessel blind spot: a vessel that switches AIS off
is invisible to AIS matching, but its hull still reflects radar — so YOLO can
confirm a contact the AIS-based feed cannot identify.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.store.repository import repo

router = APIRouter()

# YOLO cold start (Cloud Run) + torch load + Sentinel-1 fetch + inference can
# take a while on the first call; allow generous headroom.
_TIMEOUT = httpx.Timeout(120.0)

# How much to raise an event's risk when our own model independently confirms it.
_AGREEMENT_BOOST = 0.10


def _configured() -> bool:
    return bool(settings.yolo_service_url)


@router.get("/verify/yolo/status")
def verify_status() -> dict[str, object]:
    return {"configured": _configured()}


@router.post("/verify/yolo")
def verify_yolo(
    lat: float = Query(..., description="Latitude of the point to verify"),
    lon: float = Query(..., description="Longitude of the point to verify"),
    date: str = Query(..., description="ISO timestamp used to pick the Sentinel-1 scene"),
    event_id: str | None = Query(
        default=None,
        description="Optional detection id; when it still exists in the live store, "
        "an agreement boost is applied to it.",
    ),
) -> dict[str, object]:
    """Run the YOLO model on the live Sentinel-1 chip for a given point.

    Verification is a pure point lookup (lat/lon/date -> Sentinel-1 -> model), so
    it never depends on the event being present in the in-memory store. The store
    is refreshed by live ingestion, so an event the operator selected a moment ago
    may already be gone; passing coordinates directly makes the check robust to
    that. ``event_id`` is optional and only used to apply the agreement boost when
    the detection is still loaded.
    """
    if not _configured():
        raise HTTPException(
            status_code=503,
            detail="YOLO service is not configured. Set YOLO_SERVICE_URL.",
        )

    url = f"{settings.yolo_service_url.rstrip('/')}/detect-point"
    try:
        resp = httpx.post(
            url,
            json={"lat": lat, "lon": lon, "date": date},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"YOLO service error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach YOLO service: {exc}") from exc

    result = resp.json()

    # When our own model confirms a vessel at the GFW point, the two independent
    # systems agree — raise the risk and annotate, so the map reflects it. This
    # only applies when the detection is still in the live store.
    agreement = bool(result.get("found"))
    updated_event = None
    if agreement and event_id:
        event = repo.get(event_id)
        if event is not None:
            new_score = min(0.99, round(event.risk_score + _AGREEMENT_BOOST, 3))
            method = event.matching_method
            if "YOLO-confirmed" not in method:
                method = f"{method} · YOLO-confirmed (Sentinel-1)".lstrip(" ·")
            updated = event.model_copy(
                update={"risk_score": new_score, "matching_method": method}
            )
            # In-memory only (persist=False): keep the seed file as offline fallback.
            repo.upsert_many([updated], persist=False)
            updated_event = updated.model_dump()

    return {
        "event_id": event_id,
        "agreement": agreement,
        "yolo": result,
        "updated_event": updated_event,
    }
