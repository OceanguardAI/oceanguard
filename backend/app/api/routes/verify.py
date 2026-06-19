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

import math
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# --- Area sweep tuning ---
# A YOLO inference chip is ~0.04° wide (see yolo-service chip_half_deg=0.02), so
# tile a swept area at roughly that spacing. Cap the tile count so one sweep
# stays bounded in time/cost (each tile = a Sentinel-1 fetch + inference).
_SWEEP_TILE_DEG = 0.04
_SWEEP_MAX_TILES = 12
# A swept radar contact is "confirmed" (agrees with the AIS-based feed) when a
# known detection sits within this radius; otherwise it is a NEW contact our
# model surfaced that the feed missed — the actionable dark-vessel candidate.
_SWEEP_MATCH_KM = 2.0
# Fan-out width; matches the YOLO service's request concurrency.
_SWEEP_WORKERS = 4


def _configured() -> bool:
    return bool(settings.yolo_service_url)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


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


def _tile_centers(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float
) -> tuple[list[tuple[float, float]], float]:
    """Evenly tile a bbox into at most _SWEEP_MAX_TILES chip-sized cells.

    Returns the list of (lat, lon) tile centres and the effective tile spacing in
    degrees (so the caller can tell whether the area was fully covered or only
    sampled when it was too large for the tile cap).
    """
    width = max(max_lon - min_lon, 1e-6)
    height = max(max_lat - min_lat, 1e-6)

    step = _SWEEP_TILE_DEG
    nx = max(1, math.ceil(width / step))
    ny = max(1, math.ceil(height / step))
    # Coarsen the grid until it fits the tile budget — sampling rather than
    # refusing, so a sweep of a large area still returns something useful.
    while nx * ny > _SWEEP_MAX_TILES:
        step *= 1.25
        nx = max(1, math.ceil(width / step))
        ny = max(1, math.ceil(height / step))

    centers: list[tuple[float, float]] = []
    for i in range(nx):
        for j in range(ny):
            lon = min_lon + (i + 0.5) * width / nx
            lat = min_lat + (j + 0.5) * height / ny
            centers.append((lat, lon))
    effective_deg = round(max(width / nx, height / ny), 4)
    return centers, effective_deg


@router.post("/verify/yolo/sweep")
def sweep_area(
    min_lon: float = Query(..., description="West edge of the area to sweep"),
    min_lat: float = Query(..., description="South edge"),
    max_lon: float = Query(..., description="East edge"),
    max_lat: float = Query(..., description="North edge"),
    date: str = Query(..., description="ISO timestamp used to pick the Sentinel-1 scene"),
) -> dict[str, object]:
    """Proactively sweep an area (e.g. an MPA) with our own SAR ship detector.

    This is the model's real job: not re-confirming a vessel the AIS-based feed
    already flagged, but scanning a protected area on the *latest* Sentinel-1 pass
    to surface radar contacts the feed missed. The area is tiled into chips, YOLO
    runs over each, and every contact is cross-referenced against the live store —
    contacts with no known detection nearby are flagged as NEW dark-vessel
    candidates worth a patrol.
    """
    if not _configured():
        raise HTTPException(
            status_code=503,
            detail="YOLO service is not configured. Set YOLO_SERVICE_URL.",
        )
    if max_lon <= min_lon or max_lat <= min_lat:
        raise HTTPException(status_code=422, detail="Invalid bounding box: max must exceed min.")

    centers, effective_deg = _tile_centers(min_lon, min_lat, max_lon, max_lat)
    url = f"{settings.yolo_service_url.rstrip('/')}/detect-point"

    def _scan(center: tuple[float, float]) -> dict[str, object]:
        lat, lon = center
        # Drop the per-tile chip PNG from the response: a dozen base64 chips would
        # bloat the payload, and the sweep only needs contact coordinates.
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(url, json={"lat": lat, "lon": lon, "date": date})
            resp.raise_for_status()
            return resp.json()

    known = repo.all()
    contacts: list[dict[str, object]] = []
    tiles_with_contacts = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=min(_SWEEP_WORKERS, len(centers))) as pool:
        futures = {pool.submit(_scan, c): c for c in centers}
        for fut in as_completed(futures):
            try:
                result = fut.result()
            except Exception:
                errors += 1
                continue
            dets = result.get("detections") or []
            if dets:
                tiles_with_contacts += 1
            for d in dets:
                lat, lon = float(d["lat"]), float(d["lon"])
                # Nearest known detection — confirms agreement vs. a new contact.
                nearest_id, nearest_km = None, None
                for ev in known:
                    km = _haversine_km(lat, lon, ev.lat, ev.lon)
                    if nearest_km is None or km < nearest_km:
                        nearest_id, nearest_km = ev.id, km
                matched = nearest_km is not None and nearest_km <= _SWEEP_MATCH_KM
                contacts.append(
                    {
                        "lat": round(lat, 6),
                        "lon": round(lon, 6),
                        "confidence": d.get("confidence"),
                        "status": "confirmed" if matched else "new",
                        "matched_event_id": nearest_id if matched else None,
                        "nearest_known_km": round(nearest_km, 2) if nearest_km is not None else None,
                    }
                )

    contacts.sort(key=lambda c: (c["status"] != "new", -(c.get("confidence") or 0)))
    new_contacts = [c for c in contacts if c["status"] == "new"]

    return {
        "bbox": [min_lon, min_lat, max_lon, max_lat],
        "tiles_scanned": len(centers),
        "tiles_failed": errors,
        "tiles_with_contacts": tiles_with_contacts,
        "effective_tile_deg": effective_deg,
        "fully_covered": effective_deg <= _SWEEP_TILE_DEG + 1e-9,
        "total_contacts": len(contacts),
        "new_contacts": len(new_contacts),
        "confirmed_contacts": len(contacts) - len(new_contacts),
        "contacts": contacts,
    }
