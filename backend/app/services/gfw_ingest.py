"""Live data ingestion from the Global Fishing Watch (GFW) API.

Pulls SAR (synthetic-aperture radar) vessel detections for the monitored
region and converts them into RiskEvent records. The key signal for dark
fishing is a SAR detection that GFW could *not* match to an AIS broadcast:
the satellite saw a vessel, but no transponder identity exists for it.

GFW does the SAR <-> AIS cross-match server-side. In the report response an
entry that carries vessel identity fields (mmsi / shipName / vesselId) is an
AIS-matched vessel; an entry with those fields empty is a dark detection.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.models.schemas import RiskEvent
from app.services import mpa_index

GFW_BASE_URL = "https://gateway.api.globalfishingwatch.org"
SAR_DATASET = "public-global-sar-presence:latest"

# Fallback MPA name when no protected area is loaded/near a detection.
MPA_NAME = "Bar Reef Marine Sanctuary"

CONFIDENCE_THRESHOLD = 0.45


def ingestion_enabled() -> bool:
    return bool(settings.gfw_api_token)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _nearest_port(lat: float, lon: float, ports: list[dict[str, Any]]) -> tuple[str | None, float | None]:
    if not ports:
        return None, None
    best = min(ports, key=lambda p: _haversine_km(lat, lon, p["lat"], p["lon"]))
    return best.get("name"), round(_haversine_km(lat, lon, best["lat"], best["lon"]), 2)


def _score_detection(*, ais_matched: bool, distance_to_mpa_km: float, detections: int) -> tuple[float, str]:
    """Risk score for a SAR detection.

    Proximity to a protected area is the primary driver, so scores spread across
    the full range globally: a SAR vessel inside an MPA is CRITICAL, near is
    HIGH, in the surrounding waters MEDIUM, and well out in the open ocean LOW.
    Lacking an AIS identity ("dark") adds a moderate amount on top.
    """
    score = 0.25  # baseline SAR vessel presence
    if not ais_matched:
        score += 0.20  # no AIS identity in the SAR feed — possible dark vessel
    if distance_to_mpa_km <= 0:
        score += 0.45  # inside the protected area
    elif distance_to_mpa_km <= 10:
        score += 0.30  # near the boundary
    elif distance_to_mpa_km <= 50:
        score += 0.15  # in surrounding waters
    if detections > 1:
        score += 0.05  # repeated presence at the same cell
    score = min(score, 0.99)

    if score >= 0.80:
        level = "CRITICAL"
    elif score >= 0.60:
        level = "HIGH"
    elif score >= 0.45:
        level = "MEDIUM"
    else:
        level = "LOW"
    return round(score, 2), level


def _fetch_sar_report() -> list[dict[str, Any]]:
    """Call the GFW 4wings report endpoint and return raw detection entries."""
    min_lon, min_lat, max_lon, max_lat = settings.gfw_region_bbox
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=settings.gfw_lookback_days)

    params = {
        "spatial-resolution": "HIGH",
        "temporal-resolution": "ENTIRE",
        "datasets[0]": SAR_DATASET,
        "date-range": f"{start.isoformat()},{end.isoformat()}",
        "format": "JSON",
    }
    body = {
        "geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat],
                ]
            ],
        }
    }
    headers = {
        "Authorization": f"Bearer {settings.gfw_api_token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=90.0) as client:
        resp = client.post(
            f"{GFW_BASE_URL}/v3/4wings/report",
            params=params,
            json=body,
            headers=headers,
        )
        resp.raise_for_status()
        payload = resp.json()

    entries: list[dict[str, Any]] = []
    for group in payload.get("entries", []):
        # Each entry is a dict keyed by the dataset version, e.g.
        # {"public-global-sar-presence:v4.0": [ {detection}, ... ]}.
        for rows in group.values():
            if isinstance(rows, list):
                entries.extend(rows)
    return entries


def _to_risk_event(row: dict[str, Any], index: int, ports: list[dict[str, Any]]) -> RiskEvent:
    lat = float(row.get("lat", 0.0))
    lon = float(row.get("lon", 0.0))
    detections = int(row.get("detections", 1) or 1)

    # Identity fields populated => GFW matched this SAR hit to an AIS vessel.
    ais_matched = bool(row.get("vesselId") or row.get("mmsi") or row.get("shipName"))

    # Nearest protected area across the full loaded MPA set (WDPA or fallback).
    mpa_name, distance_to_mpa, inside_mpa, near_mpa = mpa_index.get_index().nearest(lat, lon)
    if mpa_name is None:  # no MPA data loaded — degrade to the named default
        mpa_name = MPA_NAME
    if distance_to_mpa == float("inf"):
        distance_to_mpa = 0.0
    port_name, port_dist = _nearest_port(lat, lon, ports)

    score, level = _score_detection(
        ais_matched=ais_matched,
        distance_to_mpa_km=distance_to_mpa,
        detections=detections,
    )

    timestamp = row.get("entryTimestamp") or datetime.now(timezone.utc).isoformat()

    if ais_matched:
        ship = row.get("shipName") or row.get("mmsi") or "an AIS-matched vessel"
        why = f"SAR detection matched to {ship} ({row.get('vesselType') or 'unknown type'})."
        action = "Cross-check vessel authorization; likely legitimate traffic."
    else:
        why = (
            "SAR detected a vessel with no matching AIS broadcast (dark vessel). "
            f"{'Inside' if inside_mpa else f'{distance_to_mpa:.1f} km from'} the protected area."
        )
        action = "Prioritize for patrol verification — possible unauthorized activity."

    return RiskEvent(
        id=f"gfw-sar-{index:04d}",
        source="GFW",
        lat=lat,
        lon=lon,
        risk_score=score,
        risk_level=level,
        sar_confidence=min(0.5 + 0.1 * detections, 0.95),
        image_quality="Satellite SAR",
        ais_matched=ais_matched,
        ais_data_available=True,
        matching_method="GFW SAR<->AIS server-side match",
        inside_mpa=inside_mpa,
        near_mpa=near_mpa,
        mpa_name=mpa_name,
        distance_to_mpa_km=distance_to_mpa,
        distance_from_port_km=port_dist,
        nearest_port=port_name,
        timestamp=timestamp,
        review_status="Pending",
        why_flagged=why,
        uncertainty="",
        confidence_threshold=CONFIDENCE_THRESHOLD,
        recommended_action=action,
        thumbnail=None,
    )


def fetch_live_events(ports: list[dict[str, Any]] | None = None) -> list[RiskEvent]:
    """Fetch and convert live GFW SAR detections into RiskEvent records."""
    rows = _fetch_sar_report()
    ports = ports or []
    events = [_to_risk_event(row, i + 1, ports) for i, row in enumerate(rows)]
    # Highest-risk first so summaries surface dark vessels near protected areas.
    events.sort(key=lambda e: e.risk_score, reverse=True)

    # A global query returns tens of thousands of detections, often clustered.
    # Keep the highest-risk detection per ~0.5deg cell so the map shows activity
    # spread across the world (and a realistic mix of risk levels) rather than
    # hundreds of identical markers piled on a handful of protected areas.
    best_per_cell: dict[tuple[int, int], RiskEvent] = {}
    for event in events:  # already sorted by score desc
        cell = (round(event.lat * 2), round(event.lon * 2))
        best_per_cell.setdefault(cell, event)
    events = list(best_per_cell.values())

    # Globally there are far more dark-vessel detections inside/near MPAs than we
    # want to plot, so a pure top-N cap would show nothing but CRITICAL markers —
    # which is neither readable nor honest. Take a stratified sample instead, so
    # the map reflects a realistic risk pyramid (a few critical leads, many
    # routine open-water detections) while still surfacing every top threat.
    cap = settings.gfw_max_events
    if cap > 0 and len(events) > cap:
        by_level: dict[str, list[RiskEvent]] = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
        for event in events:  # score desc within each level
            by_level.setdefault(event.risk_level, []).append(event)
        targets = {"CRITICAL": 0.15, "HIGH": 0.30, "MEDIUM": 0.35, "LOW": 0.20}
        selected: list[RiskEvent] = []
        for level, frac in targets.items():
            selected.extend(by_level.get(level, [])[: round(cap * frac)])
        # If some levels were short, top up with the next-highest-risk remainder.
        if len(selected) < cap:
            chosen = {id(e) for e in selected}
            for event in events:
                if len(selected) >= cap:
                    break
                if id(event) not in chosen:
                    selected.append(event)
        events = selected
        events.sort(key=lambda e: e.risk_score, reverse=True)

    # Re-number ids so they read 0001..N in display order.
    for i, event in enumerate(events, start=1):
        event.id = f"gfw-sar-{i:04d}"
    return events
