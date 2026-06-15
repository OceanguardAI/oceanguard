"""Run the full non-training ML workflow from artifacts to backend handoff."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_risk_events import build_events, resolve_source_root
from sync_outputs_to_backend import sync_outputs
from validate_artifacts import inspect_artifacts
from validate_model import inspect_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full ML workflow.")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="Artifact root containing data/, models/, and outputs/ folders.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs",
        help="Directory where risk_events.json and workflow summary should be written.",
    )
    parser.add_argument(
        "--backend-data-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "backend" / "data",
        help="Destination backend/data directory for handoff artifacts.",
    )
    parser.add_argument(
        "--skip-model-check",
        action="store_true",
        help="Skip loading best.pt before building outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    artifact_summary = inspect_artifacts(args.source_root)
    data_dir, detections_dir = resolve_source_root(args.source_root)
    source_root = data_dir.parent

    model_summary = None
    model_path = source_root / "models" / "best.pt"
    if not args.skip_model_check and model_path.exists():
        model_summary = inspect_model(model_path)

    events = build_events(source_root=source_root, output_dir=output_dir)
    risk_events_path = output_dir / "risk_events.json"
    with risk_events_path.open("w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

    source_geojson = data_dir / "bar_reef.geojson"
    risk_dest, geo_dest = sync_outputs(risk_events_path, source_geojson, args.backend_data_dir)

    gfw_count = sum(1 for event in events if event["source"] == "GFW")
    yolo_count = sum(1 for event in events if event["source"] == "YOLO_SAR")
    bar003 = next((event for event in events if event["id"] == "bar-reef-003"), None)

    workflow_summary = {
        "source_root": str(source_root),
        "artifact_summary": artifact_summary,
        "model_summary": model_summary,
        "risk_events_path": str(risk_events_path),
        "backend_risk_events_path": str(risk_dest),
        "backend_geojson_path": str(geo_dest),
        "total_events": len(events),
        "gfw_events": gfw_count,
        "yolo_events": yolo_count,
        "bar_reef_003": {
            "risk_score": bar003["risk_score"] if bar003 else None,
            "risk_level": bar003["risk_level"] if bar003 else None,
            "timestamp": bar003["timestamp"] if bar003 else None,
            "near_mpa": bar003["near_mpa"] if bar003 else None,
            "distance_to_mpa_km": bar003["distance_to_mpa_km"] if bar003 else None,
        },
    }

    summary_path = output_dir / "ml_workflow_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(workflow_summary, f, indent=2)

    print(f"Workflow summary written to: {summary_path}")
    print(f"Total events: {len(events)}")
    print(f"GFW events: {gfw_count}")
    print(f"YOLO events: {yolo_count}")
    if bar003:
        print(
            "bar-reef-003: "
            f"{bar003['risk_score']} / {bar003['risk_level']} / {bar003['timestamp']}"
        )


if __name__ == "__main__":
    main()
