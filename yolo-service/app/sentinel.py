"""Fetch a tight, high-resolution Sentinel-1 VV chip for YOLO inference.

Unlike the backend's display chip (wide, for human viewing), this pulls a
smaller, denser window centred on the suspect point so the HRSID-trained model
sees vessels at close to its training resolution. Returns 8-bit PNG bytes plus
the chip's geographic bbox, which lets the caller map detection pixels back to
latitude/longitude by simple linear interpolation (the chip is small and in
EPSG:4326).
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

# Sentinel-1 revisit is ~6-12 days; widen the search window so a scene is found.
_SEARCH_WINDOW_DAYS = 12

# VV backscatter stretched to 8-bit grayscale — bright vessels on dark water,
# matching the amplitude look the model was trained on.
_EVALSCRIPT = """//VERSION=3
function setup() {
  return { input: ["VV"], output: { bands: 1 } };
}
function evaluatePixel(s) {
  return [Math.max(0, Math.min(1, 2.5 * s.VV))];
}
"""

_token: str | None = None
_token_expiry: float = 0.0
_token_lock = threading.Lock()


def is_configured() -> bool:
    return bool(settings.sentinelhub_client_id and settings.sentinelhub_client_secret)


def _get_token() -> str:
    """Return a cached OAuth access token, refreshing shortly before expiry."""
    global _token, _token_expiry
    with _token_lock:
        if _token and time.time() < _token_expiry - 60:
            return _token
        resp = httpx.post(
            settings.sentinelhub_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.sentinelhub_client_id,
                "client_secret": settings.sentinelhub_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )
        resp.raise_for_status()
        payload = resp.json()
        _token = payload["access_token"]
        _token_expiry = time.time() + float(payload.get("expires_in", 3600))
        return _token


def _time_range(date: str | None) -> tuple[str, str]:
    """Build a [from, to] ISO range ending at `date` (default: now)."""
    try:
        end = datetime.fromisoformat(date.replace("Z", "")) if date else datetime.now(timezone.utc)
    except (ValueError, AttributeError):
        end = datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    start = end - timedelta(days=_SEARCH_WINDOW_DAYS)
    return (
        start.strftime("%Y-%m-%dT00:00:00Z"),
        (end + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z"),
    )


def fetch_chip(lat: float, lon: float, date: str | None = None) -> tuple[bytes, list[float]]:
    """Fetch a Sentinel-1 VV chip (PNG bytes) and its [min_lon,min_lat,max_lon,max_lat].

    Raises RuntimeError if Sentinel Hub is not configured; propagates httpx
    errors so the route can map them to an HTTP status.
    """
    if not is_configured():
        raise RuntimeError("Sentinel Hub is not configured.")

    half = settings.chip_half_deg
    bbox = [lon - half, lat - half, lon + half, lat + half]
    time_from, time_to = _time_range(date)
    body = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [
                {
                    "type": "sentinel-1-grd",
                    "dataFilter": {
                        "timeRange": {"from": time_from, "to": time_to},
                        "acquisitionMode": "IW",
                        "polarization": "DV",
                    },
                }
            ],
        },
        "output": {
            "width": settings.chip_px,
            "height": settings.chip_px,
            "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
        },
        "evalscript": _EVALSCRIPT,
    }

    resp = httpx.post(
        settings.sentinelhub_process_url,
        json=body,
        headers={"Authorization": f"Bearer {_get_token()}", "Accept": "image/png"},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.content, bbox
