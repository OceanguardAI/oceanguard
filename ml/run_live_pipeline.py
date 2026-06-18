"""Live SAR detection pipeline: Sentinel-1 -> YOLO -> risk events -> backend.

STATUS: EXPERIMENTAL. The pipeline runs end-to-end, but best.pt was trained on
xView3 SAR and shows a domain gap on Sentinel-1 GRD imagery: detections fire
only at very low confidence (~0.15), below the 0.45 production threshold. Do not
lower the threshold to force detections (speckle/land-edge false positives).
Use the GFW SAR path (backend) as the production dark-vessel detector until the
model is fine-tuned or a Sentinel-1 threshold is validated against ground truth.

End-to-end, this turns the trained model into a live detector:
  1. fetch a fresh Sentinel-1 GeoTIFF for the monitored bbox (Copernicus)
  2. tile it and run YOLO (best.pt) over the tiles
  3. georeference detections using the tile's own CRS/transform
  4. enrich (MPA distance, nearest port) and score risk
  5. emit risk_events.json and optionally push them to the backend

AIS cross-checking for these detections is done by the backend's
POST /ais/verify-dark, where the AISStream client lives.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from fetch_sentinel1 import fetch_sentinel1_tif
from pipeline.detect import detect_tiles
from pipeline.enrich import classify_mpa, distance_to_mpa, load_mpa, nearest_port_distance
from pipeline.georeference import georeference_from_tif
from pipeline.risk import calculate_risk
from pipeline.tiling import tile_sar

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"
MPA_NAME = "Bar Reef Marine Sanctuary"
CONFIDENCE_THRESHOLD = 0.45
RECOMMENDED_ACTION = "Human reviewer should verify scene and external context."


def _bbox_inside(lat: float, lon: float, bbox: list[float]) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def build_yolo_events(
    georeferenced: list[dict],
    mpa_geojson: Path,
    ports_json: Path,
    scene_timestamp: str,
) -> list[dict]:
    mpa_polygon = load_mpa(mpa_geojson)
    events: list[dict] = []

    for index, det in enumerate(georeferenced, start=1):
        lat, lon = det["lat"], det["lon"]
        distance_km = distance_to_mpa(lat, lon, mpa_polygon)
        inside_mpa, near_mpa = classify_mpa(distance_km)

        port_distance_km, port_name = (None, None)
        if ports_json.exists():
            port_distance_km, port_name = nearest_port_distance(lat, lon, ports_json)

        confidence = float(det.get("confidence", 0.5))
        risk_score, risk_level = calculate_risk(
            detection_conf=confidence,
            ais_matched=False,
            ais_data_available=False,  # backend /ais/verify-dark enriches this
            inside_mpa=inside_mpa,
            near_mpa=near_mpa,
            image_quality_score=1.0,
        )

        events.append(
            {
                "id": f"yolo-live-{index:04d}",
                "source": "YOLO_SAR",
                "lat": lat,
                "lon": lon,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "sar_confidence": round(confidence, 3),
                "image_quality": "Sentinel-1 GRD",
                "ais_matched": False,
                "ais_data_available": False,
                "matching_method": "YOLO SAR detection (live Sentinel-1)",
                "inside_mpa": inside_mpa,
                "near_mpa": near_mpa,
                "mpa_name": MPA_NAME if (inside_mpa or near_mpa) else None,
                "distance_to_mpa_km": distance_km,
                "distance_from_port_km": port_distance_km,
                "nearest_port": port_name,
                "timestamp": scene_timestamp,
                "review_status": "Pending",
                "why_flagged": "",
                "uncertainty": "",
                "confidence_threshold": CONFIDENCE_THRESHOLD,
                "recommended_action": RECOMMENDED_ACTION,
                "thumbnail": None,
            }
        )
    return events


def run(
    bbox: list[float],
    model_path: Path,
    tif_path: Path | None,
    backend_url: str | None,
    lookback_days: int,
) -> list[dict]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    tiles_dir = BASE_DIR / "tiles_live"

    # 1. Fetch fresh imagery unless a local tif was supplied (testing/offline).
    if tif_path is None:
        client_id = os.environ.get("COPERNICUS_CLIENT_ID", "")
        client_secret = os.environ.get("COPERNICUS_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise SystemExit(
                "COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET must be set to fetch live imagery, "
                "or pass --tif-path to run on a local scene."
            )
        tif_path = DATA_DIR / "sentinel1_live.tif"
        fetch_sentinel1_tif(bbox, tif_path, client_id, client_secret, lookback_days)

    # 2-3. Tile, detect, georeference using the scene's real transform.
    tile_sar(str(tif_path), str(tiles_dir))
    detections = detect_tiles(str(tiles_dir), str(model_path), conf_threshold=CONFIDENCE_THRESHOLD)
    georeferenced = georeference_from_tif(detections, str(tif_path))

    # Keep only detections that fall inside the monitored bbox.
    georeferenced = [d for d in georeferenced if _bbox_inside(d["lat"], d["lon"], bbox)]

    # 4. Enrich + score.
    scene_timestamp = datetime.now(timezone.utc).isoformat()
    events = build_yolo_events(
        georeferenced,
        DATA_DIR / "bar_reef.geojson",
        DATA_DIR / "overpass_bar_reef_ports.json",
        scene_timestamp,
    )

    # 5. Emit and optionally push.
    out_path = OUTPUTS_DIR / "risk_events_live.json"
    out_path.write_text(json.dumps(events, indent=2), encoding="utf-8")
    print(f"Wrote {len(events)} YOLO_SAR events to {out_path}")

    if backend_url:
        import requests

        resp = requests.post(
            f"{backend_url.rstrip('/')}/ingest/push?mode=merge",
            json=events,
            timeout=60,
        )
        resp.raise_for_status()
        print(f"Pushed to backend: {resp.json()}")

    return events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the live Sentinel-1 -> YOLO -> backend pipeline.")
    parser.add_argument(
        "--bbox", type=float, nargs=4,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        default=[79.4, 8.0, 79.9, 8.8],
    )
    parser.add_argument("--model-path", type=Path, default=BASE_DIR / "models" / "best.pt")
    parser.add_argument(
        "--tif-path", type=Path, default=None,
        help="Run on a local GeoTIFF instead of fetching from Copernicus.",
    )
    parser.add_argument(
        "--backend-url", type=str, default=None,
        help="If set, POST events to <url>/ingest/push (e.g. http://localhost:8000).",
    )
    parser.add_argument("--lookback-days", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(
        bbox=args.bbox,
        model_path=args.model_path,
        tif_path=args.tif_path,
        backend_url=args.backend_url,
        lookback_days=args.lookback_days,
    )


if __name__ == "__main__":
    main()
