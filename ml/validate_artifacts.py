"""Validate ML input artifacts before running the pipeline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_risk_events import DEFAULT_SOURCE_ROOT, resolve_source_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ML artifact files and shapes.")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="Artifact root containing data/ and outputs/ folders.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir, outputs_dir = resolve_source_root(args.source_root)

    print(f"Resolved source root data dir: {data_dir}")
    print(f"Resolved source root outputs dir: {outputs_dir}")
    if data_dir.parent == DEFAULT_SOURCE_ROOT:
        print("Using temporary ML artifact cache.")

    required = {
        "bar_reef.geojson": data_dir / "bar_reef.geojson",
        "gfw_bar_reef_sar_unmatched.json": data_dir / "gfw_bar_reef_sar_unmatched.json",
        "overpass_bar_reef_ports.json": data_dir / "overpass_bar_reef_ports.json",
        "detections_scene1_georef.json": outputs_dir / "detections_scene1_georef.json",
    }

    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required artifacts: {', '.join(missing)}")

    with required["gfw_bar_reef_sar_unmatched.json"].open(encoding="utf-8") as f:
        gfw = json.load(f)
    with required["overpass_bar_reef_ports.json"].open(encoding="utf-8") as f:
        ports = json.load(f)
    with required["bar_reef.geojson"].open(encoding="utf-8") as f:
        geojson = json.load(f)
    with required["detections_scene1_georef.json"].open(encoding="utf-8") as f:
        detections = json.load(f)

    gfw_entries = []
    if isinstance(gfw, list):
        gfw_entries = gfw
    elif isinstance(gfw, dict):
        for key in ("entries", "results", "data", "detections"):
            if isinstance(gfw.get(key), list):
                gfw_entries = gfw[key]
                break

    print(f"GFW detections: {len(gfw_entries)}")
    print(f"Port elements: {len(ports.get('elements', []))}")
    print(f"GeoJSON type: {geojson.get('type')}")
    print(f"YOLO detections: {len(detections)}")

    if gfw_entries:
        first_gfw = gfw_entries[0]
        print(f"First GFW keys: {sorted(first_gfw.keys())}")
    if detections:
        first_detection = detections[0]
        print(f"First YOLO detection keys: {sorted(first_detection.keys())}")

    if len(detections) != 122:
        print("Warning: expected 122 YOLO detections for the xView3 validation scene.")


if __name__ == "__main__":
    main()
