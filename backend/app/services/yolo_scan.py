"""Turn GFW SAR-presence cells into YOLO-verified candidate events.

GFW tells us where its SAR pipeline saw vessel-like objects; it supplies no image.
For the most relevant cells we ask the YOLO service to fetch a fresh Sentinel-1
chip and run our own detector, then store each contact as a `YOLO_SAR` event.

A contact is a model candidate only: the service returns no scene timestamp and
AIS has not been checked, so the score never claims a dark vessel.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256

import httpx

from app.core.config import settings
from app.models.schemas import ActivityAggregate, RiskEvent
from app.services import mpa_index

_log = logging.getLogger(__name__)

SOURCE = "YOLO_SAR"
_TIMEOUT = httpx.Timeout(120.0)
_WORKERS = 2
# Rank at most this many top-count cells by MPA proximity (bounds shapely work).
_RANK_POOL = 300


def scan_enabled() -> bool:
    return bool(settings.yolo_scan_enabled and settings.yolo_service_url)


def select_cells(cells: list[ActivityAggregate], top_n: int) -> list[ActivityAggregate]:
    """Pick the cells most worth a Sentinel Hub request.

    Inside/near an MPA first, then by GFW detection count.
    """
    pool = sorted(cells, key=lambda c: c.detection_count, reverse=True)[:_RANK_POOL]
    index = mpa_index.get_index()
    ranked: list[tuple[tuple[int, int, int], ActivityAggregate]] = []
    for cell in pool:
        if cell.detection_count < settings.yolo_scan_min_cell_detections:
            continue
        _, _, inside, near = index.nearest(cell.lat, cell.lon)
        ranked.append(((int(inside), int(near), cell.detection_count), cell))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [cell for _, cell in ranked[:top_n]]


def _detect(lat: float, lon: float, date: str) -> dict:
    resp = httpx.post(
        f"{settings.yolo_service_url.rstrip('/')}/detect-point",
        json={"lat": lat, "lon": lon, "date": date},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _level(score: float) -> str:
    if score >= 0.80:
        return "CRITICAL"
    if score >= 0.60:
        return "HIGH"
    if score >= 0.45:
        return "MEDIUM"
    return "LOW"


def build_event(det: dict, cell: ActivityAggregate, scanned_at: datetime) -> RiskEvent:
    lat, lon = float(det["lat"]), float(det["lon"])
    conf = float(det["confidence"])
    name, dist_km, inside, near = mpa_index.get_index().nearest(lat, lon)
    near = near and not inside

    # Same MPA-proximity terms as the live additive formula, but no "no AIS
    # identity" term: AIS has not been checked for this contact.
    score = 0.25
    score += 0.45 if inside else 0.30 if near else 0.0
    score += 0.10 if conf >= 0.5 else 0.0
    score = round(min(score, 0.99), 2)

    digest = sha256(f"{lat:.4f}|{lon:.4f}|{scanned_at.date()}".encode()).hexdigest()[:10]
    where = (
        f"inside {name}" if inside
        else f"{dist_km:.1f} km from {name}" if near and name
        else "outside any known protected area"
    )
    finite_dist = dist_km if dist_km != float("inf") else None
    return RiskEvent(
        id=f"yolo-sar-{digest}",
        source=SOURCE,
        lat=lat,
        lon=lon,
        risk_score=score,
        risk_level=_level(score),
        sar_confidence=round(conf, 3),
        image_quality="unassessed",
        ais_matched=False,
        ais_data_available=False,
        matching_method="not_checked",
        inside_mpa=inside,
        near_mpa=near,
        mpa_name=name if (inside or near) else None,
        distance_to_mpa_km=finite_dist,
        distance_from_port_km=None,
        nearest_port=None,
        timestamp=scanned_at.isoformat().replace("+00:00", "Z"),
        review_status="Pending",
        why_flagged=(
            f"YOLO detected a ship-like object (confidence {conf:.2f}) in a Sentinel-1 chip, "
            f"{where}. GFW SAR presence reported {cell.detection_count} detection(s) in this cell."
        ),
        uncertainty=(
            "Model candidate only. AIS was not checked, so this is not a confirmed dark vessel. "
            "The chip's acquisition time is unknown (up to ~12 days old), and the detector was "
            "trained on HRSID, with small-vessel recall on 10 m Sentinel-1 unmeasured."
        ),
        confidence_threshold=0.25,
        recommended_action="Cross-check AIS and the latest scene before any patrol tasking.",
        thumbnail=None,
    )


def scan_cells(cells: list[ActivityAggregate], *, top_n: int | None = None) -> dict[str, object]:
    """Scan the selected cells and upsert resulting events into the repository."""
    from app.store.repository import repo

    top_n = settings.yolo_scan_top_n if top_n is None else top_n
    selected = select_cells(cells, top_n)
    scanned_at = datetime.now(timezone.utc)
    date = scanned_at.isoformat().replace("+00:00", "Z")

    def _one(cell: ActivityAggregate) -> list[RiskEvent] | None:
        try:
            result = _detect(cell.lat, cell.lon, date)
        except Exception as exc:
            _log.warning("YOLO scan failed for cell (%.3f, %.3f): %s", cell.lat, cell.lon, exc)
            return None
        return [build_event(d, cell, scanned_at) for d in (result.get("detections") or [])]

    events: list[RiskEvent] = []
    failed = 0
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        for outcome in pool.map(_one, selected):
            if outcome is None:
                failed += 1
            else:
                events.extend(outcome)

    unique = {e.id: e for e in events}
    if unique:
        repo.upsert_many(list(unique.values()))
    return {
        "cells_considered": len(cells),
        "cells_scanned": len(selected),
        "cells_failed": failed,
        "events_upserted": len(unique),
    }
