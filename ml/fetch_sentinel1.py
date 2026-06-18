"""Fetch a Sentinel-1 SAR GeoTIFF for the monitored region via Copernicus.

Uses the Copernicus Data Space Ecosystem (free tier) Sentinel Hub Process API:
  1. OAuth client-credentials  -> access token
  2. POST /api/v1/process with a Sentinel-1 evalscript -> VH-polarization
     backscatter (dB) GeoTIFF clipped to the bounding box.

Credentials (create an OAuth client at https://shapps.dataspace.copernicus.eu/
dashboard/#/account/settings) are read from the environment:
  COPERNICUS_CLIENT_ID, COPERNICUS_CLIENT_SECRET

The output GeoTIFF carries its CRS + affine transform, which the live pipeline
reads with rasterio to georeference YOLO detections (no hardcoded transform).
"""
from __future__ import annotations

import argparse
import math
import os
from datetime import date, timedelta
from pathlib import Path

import requests

TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
MAX_DIM = 2500  # Process API hard cap on output width/height (px).

# VH backscatter in dB, normalized to a single float32 band. The pipeline's
# tiling step expects raw dB values (it clips to [-50, 0] dB internally).
EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["VH"] }],
    output: { bands: 1, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(s) {
  // Linear -> dB. Guard against log(0).
  var vh = s.VH > 0 ? 10 * Math.log(s.VH) / Math.LN10 : -50;
  return [vh];
}
"""


def get_access_token(client_id: str, client_secret: str) -> str:
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _window_for_resolution(bbox: list[float], resolution_m: float) -> tuple[list[float], int, int]:
    """Return (bbox, width, height) at `resolution_m` per pixel.

    Vessel detection needs ~10 m/px, but the Process API caps output at
    MAX_DIM px. If the full bbox would exceed that, we center-crop the bbox to
    the largest window that fits at the target resolution (better to see a
    smaller area sharply than the whole region too blurred to detect vessels).
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    mid_lat = (min_lat + max_lat) / 2
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * abs(math.cos(math.radians(mid_lat)))

    width_px = round((max_lon - min_lon) * m_per_deg_lon / resolution_m)
    height_px = round((max_lat - min_lat) * m_per_deg_lat / resolution_m)

    if width_px <= MAX_DIM and height_px <= MAX_DIM:
        return bbox, max(64, width_px), max(64, height_px)

    # Too large at target resolution: center a MAX_DIM-px window on the bbox.
    win_w_deg = MAX_DIM * resolution_m / m_per_deg_lon
    win_h_deg = MAX_DIM * resolution_m / m_per_deg_lat
    c_lon, c_lat = (min_lon + max_lon) / 2, (min_lat + max_lat) / 2
    cropped = [
        max(min_lon, c_lon - win_w_deg / 2),
        max(min_lat, c_lat - win_h_deg / 2),
        min(max_lon, c_lon + win_w_deg / 2),
        min(max_lat, c_lat + win_h_deg / 2),
    ]
    print(
        f"  bbox needs {width_px}x{height_px}px at {resolution_m}m/px (> {MAX_DIM}); "
        f"centering a {MAX_DIM}px window: {[round(v, 4) for v in cropped]}"
    )
    return cropped, MAX_DIM, MAX_DIM


def fetch_sentinel1_tif(
    bbox: list[float],
    out_path: Path,
    client_id: str,
    client_secret: str,
    lookback_days: int = 12,
    resolution_m: float = 10.0,
) -> Path:
    """Download the most recent Sentinel-1 GRD VH scene over `bbox` as GeoTIFF.

    Uses mosaickingOrder=mostRecent so a single recent pass is returned rather
    than a multi-day composite (compositing blurs moving vessels).
    """
    token = get_access_token(client_id, client_secret)
    fetch_bbox, width, height = _window_for_resolution(bbox, resolution_m)
    end = date.today()
    start = end - timedelta(days=lookback_days)

    payload = {
        "input": {
            "bounds": {
                "bbox": fetch_bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [
                {
                    "type": "sentinel-1-grd",
                    "dataFilter": {
                        "timeRange": {
                            "from": f"{start.isoformat()}T00:00:00Z",
                            "to": f"{end.isoformat()}T23:59:59Z",
                        },
                        "mosaickingOrder": "mostRecent",
                    },
                    "processing": {"backCoeff": "GAMMA0_TERRAIN", "orthorectify": True},
                }
            ],
        },
        "output": {
            "width": width,
            "height": height,
            "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}],
        },
        "evalscript": EVALSCRIPT,
    }

    resp = requests.post(
        PROCESS_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=180,
    )
    resp.raise_for_status()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)
    print(
        f"Sentinel-1 GeoTIFF saved: {out_path} ({width}x{height}px @ {resolution_m}m/px, {start}..{end})"
    )
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a Sentinel-1 SAR GeoTIFF via Copernicus.")
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        default=[79.4, 8.0, 79.9, 8.8],
        help="Bounding box (default = Bar Reef, Sri Lanka).",
    )
    parser.add_argument(
        "--out-path",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "sentinel1_live.tif",
    )
    parser.add_argument("--lookback-days", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client_id = os.environ.get("COPERNICUS_CLIENT_ID", "")
    client_secret = os.environ.get("COPERNICUS_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise SystemExit(
            "COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET must be set. "
            "Create an OAuth client at https://shapps.dataspace.copernicus.eu/dashboard/#/account/settings"
        )
    fetch_sentinel1_tif(
        bbox=args.bbox,
        out_path=args.out_path,
        client_id=client_id,
        client_secret=client_secret,
        lookback_days=args.lookback_days,
    )


if __name__ == "__main__":
    main()
