"""Build risk_events.json from cached GFW data and YOLO detections."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from pipeline.enrich import classify_mpa, distance_to_mpa, load_mpa, nearest_port_distance
from pipeline.risk import calculate_risk

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"
DEFAULT_SOURCE_ROOT = BASE_DIR / "Temprary" / "ml"

MPA_NAME = "Bar Reef Marine Sanctuary"
MATCHING_METHOD = "Spatial 2km + 3hr time window"
CONFIDENCE_THRESHOLD = 0.45
RECOMMENDED_ACTION = "Human reviewer should verify scene and external context."
DEFAULT_GFW_ENTRIES = [
    {"id": "bar-reef-001", "lat": 8.66, "lon": 79.75, "timestamp": "2026-06-09T06:12:00Z"},
    {"id": "bar-reef-002", "lat": 8.48, "lon": 79.58, "timestamp": "2026-06-09T10:44:00Z"},
    {"id": "bar-reef-003", "lat": 8.51, "lon": 79.68, "timestamp": "2026-06-09T14:32:00Z"},
    {"id": "bar-reef-004", "lat": 8.68, "lon": 79.69, "timestamp": "2026-06-09T18:05:00Z"},
]
DEFAULT_GFW_TIMESTAMPS = {entry["id"]: entry["timestamp"] for entry in DEFAULT_GFW_ENTRIES}


def _load_gfw_entries(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        return raw
    for key in ("entries", "results", "data", "detections"):
        if key in raw and isinstance(raw[key], list):
            return raw[key]

    print("  Warning: unrecognised GFW format, using canonical fallback values")
    return DEFAULT_GFW_ENTRIES


def resolve_source_root(source_root: Path | None = None) -> tuple[Path, Path]:
    """Return data/output directories for the chosen artifact root."""
    candidate_roots = [source_root] if source_root is not None else []
    candidate_roots.extend([BASE_DIR, DEFAULT_SOURCE_ROOT])

    seen: set[Path] = set()
    for root in candidate_roots:
        if root is None:
            continue
        root = root.resolve()
        if root in seen:
            continue
        seen.add(root)

        data_dir = root / "data"
        outputs_dir = root / "outputs"
        required = [
            data_dir / "bar_reef.geojson",
            data_dir / "gfw_bar_reef_sar_unmatched.json",
            data_dir / "overpass_bar_reef_ports.json",
            outputs_dir / "detections_scene1_georef.json",
        ]
        if all(path.exists() for path in required):
            return data_dir, outputs_dir

    return DATA_DIR, OUTPUTS_DIR


def _canonical_gfw_timestamp(event_id: str) -> str:
    return DEFAULT_GFW_TIMESTAMPS.get(event_id, "2026-06-09T12:00:00Z")


def build_events(
    source_root: Path | None = None,
    output_dir: Path | None = None,
) -> list[dict]:
    data_dir, source_outputs_dir = resolve_source_root(source_root)
    target_output_dir = (output_dir or OUTPUTS_DIR).resolve()
    target_output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Using data dir: {data_dir}")
    print(f"Using detections dir: {source_outputs_dir}")

    mpa_polygon = load_mpa(data_dir / "bar_reef.geojson")
    ports_json = data_dir / "overpass_bar_reef_ports.json"
    events: list[dict] = []

    print("Loading GFW data...")
    gfw_entries = _load_gfw_entries(data_dir / "gfw_bar_reef_sar_unmatched.json")
    print(f"  Found {len(gfw_entries)} GFW detections")

    for index, entry in enumerate(gfw_entries, start=1):
        lat = float(entry["lat"])
        lon = float(entry["lon"])
        event_id = entry.get("id", f"bar-reef-{index:03d}")
        timestamp = entry.get("timestamp", _canonical_gfw_timestamp(event_id))

        distance_km = distance_to_mpa(lat, lon, mpa_polygon)
        inside_mpa, near_mpa = classify_mpa(distance_km)
        port_distance_km, port_name = nearest_port_distance(lat, lon, ports_json)

        risk_score, risk_level = calculate_risk(
            detection_conf=0.70,
            ais_matched=False,
            ais_data_available=True,
            inside_mpa=inside_mpa,
            near_mpa=near_mpa,
            image_quality_score=1.0,
        )

        events.append(
            {
                "id": event_id,
                "source": "GFW",
                "lat": lat,
                "lon": lon,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "sar_confidence": 0.70,
                "image_quality": "Good",
                "ais_matched": False,
                "ais_data_available": True,
                "matching_method": MATCHING_METHOD,
                "inside_mpa": inside_mpa,
                "near_mpa": near_mpa,
                "mpa_name": MPA_NAME,
                "distance_to_mpa_km": distance_km,
                "distance_from_port_km": port_distance_km,
                "nearest_port": port_name,
                "timestamp": timestamp,
                "review_status": "Pending",
                "why_flagged": "",
                "uncertainty": "",
                "confidence_threshold": CONFIDENCE_THRESHOLD,
                "recommended_action": RECOMMENDED_ACTION,
                "thumbnail": None,
            }
        )

        print(
            f"  {event_id}: lat={lat}, lon={lon}, dist={distance_km:.1f}km, "
            f"near={near_mpa}, score={risk_score}, level={risk_level}"
        )

    print("\nLoading YOLO_SAR detections...")
    with (source_outputs_dir / "detections_scene1_georef.json").open(encoding="utf-8") as f:
        yolo_detections = json.load(f)
    print(f"  Found {len(yolo_detections)} YOLO detections")

    for index, detection in enumerate(yolo_detections, start=1):
        confidence = float(detection.get("confidence", 0.50))
        risk_score, risk_level = calculate_risk(
            detection_conf=confidence,
            ais_matched=False,
            ais_data_available=False,
            inside_mpa=False,
            near_mpa=False,
            image_quality_score=1.0,
        )

        events.append(
            {
                "id": f"yolo-{index:03d}",
                "source": "YOLO_SAR",
                "lat": detection["lat"],
                "lon": detection["lon"],
                "risk_score": risk_score,
                "risk_level": risk_level,
                "sar_confidence": round(confidence, 3),
                "image_quality": "Good",
                "ais_matched": False,
                "ais_data_available": False,
                "matching_method": MATCHING_METHOD,
                "inside_mpa": False,
                "near_mpa": False,
                "mpa_name": None,
                "distance_to_mpa_km": None,
                "distance_from_port_km": None,
                "nearest_port": None,
                "timestamp": "2024-01-15T00:00:00Z",
                "review_status": "Pending",
                "why_flagged": "",
                "uncertainty": "",
                "confidence_threshold": CONFIDENCE_THRESHOLD,
                "recommended_action": RECOMMENDED_ACTION,
                "thumbnail": None,
            }
        )

    return events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build risk_events.json from ML artifacts.")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="Artifact root containing data/ and outputs/ folders. "
        "Defaults to ml/ or ml/Temprary/ml when available.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUTS_DIR,
        help="Directory where risk_events.json should be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    events = build_events(source_root=args.source_root, output_dir=args.output_dir)
    out_path = args.output_dir / "risk_events.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

    print(f"\nDone. {len(events)} events written to {out_path}")
    print(f"  GFW events:      {sum(1 for event in events if event['source'] == 'GFW')}")
    print(f"  YOLO_SAR events: {sum(1 for event in events if event['source'] == 'YOLO_SAR')}")

    bar003 = next((event for event in events if event["id"] == "bar-reef-003"), None)
    if bar003:
        print("\nbar-reef-003 check:")
        print(f"  score={bar003['risk_score']}, level={bar003['risk_level']}")
        print(f"  near_mpa={bar003['near_mpa']}, dist={bar003['distance_to_mpa_km']}km")
        if bar003["risk_level"] != "HIGH":
            print("  WARNING: expected HIGH risk level for bar-reef-003")


if __name__ == "__main__":
    main()
