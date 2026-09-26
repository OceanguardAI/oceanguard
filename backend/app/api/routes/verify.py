"""On-demand YOLO point scans; model hits do not prove event identity or risk."""
from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.services.acquisition import parse_request_time, provenance
from app.store.repository import repo

router = APIRouter()

# YOLO cold start (Cloud Run) + torch load + Sentinel-1 fetch + inference can
# take a while on the first call; allow generous headroom.
_TIMEOUT = httpx.Timeout(120.0)

# --- Area sweep tuning ---
# A YOLO inference chip is ~0.04° wide (see yolo-service chip_half_deg=0.02), so
# tile a swept area at roughly that spacing. Cap the tile count so one sweep
# stays bounded in time/cost (each tile = a Sentinel-1 fetch + inference).
_SWEEP_TILE_DEG = 0.04
_SWEEP_MAX_TILES = 12
# Spatial proximity threshold for comparing a model contact with a stored observation.
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
    lat: float = Query(..., ge=-90, le=90, description="Latitude of the point to verify"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude of the point to verify"),
    date: str = Query(..., description="ISO timestamp used to pick the Sentinel-1 scene"),
    event_id: str | None = Query(
        default=None,
        description="Optional event id for comparison; scanning does not change its risk.",
    ),
) -> dict[str, object]:
    """Run the YOLO model on the live Sentinel-1 chip for a given point.

    The inference service currently returns no scene acquisition identifier or
    capture timestamp. Its detections can be shown as nearby model candidates,
    but cannot establish agreement with a specific event.
    """
    if not _configured():
        raise HTTPException(
            status_code=503,
            detail="YOLO service is not configured. Set YOLO_SERVICE_URL.",
        )
    try:
        requested_at = parse_request_time(date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

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

    nearby = any(
        _haversine_km(lat, lon, float(d["lat"]), float(d["lon"])) <= _SWEEP_MATCH_KM
        for d in (result.get("detections") or [])
        if d.get("lat") is not None and d.get("lon") is not None
    )
    event = repo.get(event_id) if event_id else None
    spatial_match = bool(
        nearby and event and _haversine_km(lat, lon, event.lat, event.lon) <= _SWEEP_MATCH_KM
    )

    return {
        "event_id": event_id,
        "agreement": False,
        "spatial_match": spatial_match,
        "verification_status": "acquisition_unverified" if spatial_match else "no_spatial_match",
        "provenance": provenance(lat=lat, lon=lon, requested_at=requested_at, result=result),
        "yolo": result,
        "updated_event": None,
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
    min_lon: float = Query(..., ge=-180, le=180, description="West edge of the area to sweep"),
    min_lat: float = Query(..., ge=-90, le=90, description="South edge"),
    max_lon: float = Query(..., ge=-180, le=180, description="East edge"),
    max_lat: float = Query(..., ge=-90, le=90, description="North edge"),
    date: str = Query(..., description="ISO timestamp used to pick the Sentinel-1 scene"),
) -> dict[str, object]:
    """Proactively sweep an area (e.g. an MPA) with our own SAR ship detector.

    The area is tiled into chips. Each model contact is compared with stored
    observation-level model results, not GFW aggregate cells or demo cases.
    Neither a missing nearby record nor a model hit establishes AIS status.
    """
    if not _configured():
        raise HTTPException(
            status_code=503,
            detail="YOLO service is not configured. Set YOLO_SERVICE_URL.",
        )
    try:
        requested_at = parse_request_time(date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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

    known = repo.all(source="YOLO_SAR")
    contacts: list[dict[str, object]] = []
    tiles_with_contacts = 0
    tiles_with_scene_metadata = 0
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
            tile_provenance = provenance(
                lat=futures[fut][0], lon=futures[fut][1],
                requested_at=requested_at, result=result,
            )
            if tile_provenance["coverage_status"] == "scene_metadata_available":
                tiles_with_scene_metadata += 1
            if dets:
                tiles_with_contacts += 1
            for d in dets:
                lat, lon = float(d["lat"]), float(d["lon"])
                # Compare only against observation-level records.
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
        "requested_at": requested_at.isoformat().replace("+00:00", "Z"),
        "coverage_status": (
            "scene_metadata_available"
            if tiles_with_scene_metadata == len(centers) else "scene_time_unverified"
        ),
        "tiles_with_scene_metadata": tiles_with_scene_metadata,
        "total_contacts": len(contacts),
        "new_contacts": len(new_contacts),
        "confirmed_contacts": len(contacts) - len(new_contacts),
        "contacts": contacts,
    }
