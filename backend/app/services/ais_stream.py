"""Short AISStream samples for current-position context, not historical coverage."""
from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

AISSTREAM_URL = "wss://stream.aisstream.io/v0/stream"
POSITION_TYPES = {"PositionReport", "StandardClassBPositionReport", "ExtendedClassBPositionReport"}


def ais_enabled() -> bool:
    return bool(settings.aisstream_api_key)


def _bbox_for_aisstream() -> list[list[list[float]]]:
    """Convert config bbox [min_lon,min_lat,max_lon,max_lat] to AISStream
    [[[SW_lat, SW_lon], [NE_lat, NE_lon]]]."""
    min_lon, min_lat, max_lon, max_lat = settings.gfw_region_bbox
    return [[[min_lat, min_lon], [max_lat, max_lon]]]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


async def collect_ais(seconds: int = 20) -> list[dict[str, Any]]:
    """Sample live AIS for `seconds` over the monitored bbox.

    Returns the latest position per vessel as a list of dicts:
    {mmsi, ship_name, lat, lon, sog, type, timestamp}.
    """
    import websockets

    if not ais_enabled():
        raise RuntimeError("AISSTREAM_API_KEY is not configured.")

    subscription = {
        "APIKey": settings.aisstream_api_key,
        "BoundingBoxes": _bbox_for_aisstream(),
        "FilterMessageTypes": ["PositionReport", "StandardClassBPositionReport"],
    }

    vessels: dict[str, dict[str, Any]] = {}

    async def _listen(ws: Any) -> None:
        async for raw in ws:
            msg = json.loads(raw)
            if "error" in msg:
                raise RuntimeError(f"AISStream error: {msg['error']}")
            if msg.get("MessageType") not in POSITION_TYPES:
                continue
            meta = msg.get("MetaData", {})
            mmsi = str(meta.get("MMSI", "")).strip()
            if not mmsi:
                continue
            vessels[mmsi] = {
                "mmsi": mmsi,
                "ship_name": (meta.get("ShipName") or "").strip() or None,
                "lat": meta.get("latitude"),
                "lon": meta.get("longitude"),
                "timestamp": meta.get("time_utc"),
            }

    async with websockets.connect(AISSTREAM_URL, open_timeout=15) as ws:
        await ws.send(json.dumps(subscription))
        try:
            await asyncio.wait_for(_listen(ws), timeout=seconds)
        except asyncio.TimeoutError:
            pass  # expected: the sampling window elapsed

    return list(vessels.values())


def sample_association(
    lat: float,
    lon: float,
    observed_at: str | None,
    live_vessels: list[dict[str, Any]],
    *,
    radius_km: float = 2.0,
    max_age_seconds: int = 300,
) -> tuple[str, list[str]]:
    """Find recent nearby AIS candidates; a short sample cannot prove absence."""
    if not observed_at or not live_vessels:
        return "unavailable", []
    try:
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            return "unavailable", []
        age = abs((datetime.now(timezone.utc) - observed).total_seconds())
        if age > max_age_seconds:
            return "unavailable", []
    except ValueError:
        return "unavailable", []

    candidates: list[str] = []
    for vessel in live_vessels:
        if vessel.get("lat") is None or vessel.get("lon") is None:
            continue
        try:
            message_time = datetime.fromisoformat(str(vessel["timestamp"]).replace("Z", "+00:00"))
            if message_time.tzinfo is None or abs((message_time - observed).total_seconds()) > max_age_seconds:
                continue
            if _haversine_km(lat, lon, float(vessel["lat"]), float(vessel["lon"])) <= radius_km:
                candidates.append(str(vessel["mmsi"]))
        except (KeyError, TypeError, ValueError):
            continue
    if len(candidates) > 1:
        return "ambiguous", candidates
    if candidates:
        return "matched", candidates
    return "unavailable", []
