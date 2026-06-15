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


def inspect_artifacts(source_root: Path | None = None) -> dict:
    """Return a compact summary of the resolved ML artifact set."""
    data_dir, outputs_dir = resolve_source_root(source_root)
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

    return {
        "data_dir": str(data_dir),
        "outputs_dir": str(outputs_dir),
        "using_temporary_cache": data_dir.parent == DEFAULT_SOURCE_ROOT,
        "gfw_detections": len(gfw_entries),
        "port_elements": len(ports.get("elements", [])),
        "geojson_type": geojson.get("type"),
        "yolo_detections": len(detections),
        "first_gfw_keys": sorted(gfw_entries[0].keys()) if gfw_entries else [],
        "first_yolo_keys": sorted(detections[0].keys()) if detections else [],
    }


def main() -> None:
    args = parse_args()
    summary = inspect_artifacts(args.source_root)

    print(f"Resolved source root data dir: {summary['data_dir']}")
    print(f"Resolved source root outputs dir: {summary['outputs_dir']}")
    if summary["using_temporary_cache"]:
        print("Using temporary ML artifact cache.")

    print(f"GFW detections: {summary['gfw_detections']}")
    print(f"Port elements: {summary['port_elements']}")
    print(f"GeoJSON type: {summary['geojson_type']}")
    print(f"YOLO detections: {summary['yolo_detections']}")

    if summary["first_gfw_keys"]:
        print(f"First GFW keys: {summary['first_gfw_keys']}")
    if summary["first_yolo_keys"]:
        print(f"First YOLO detection keys: {summary['first_yolo_keys']}")

    if summary["yolo_detections"] != 122:
        print("Warning: expected 122 YOLO detections for the xView3 validation scene.")


if __name__ == "__main__":
    main()
