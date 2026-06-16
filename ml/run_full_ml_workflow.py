"""Run the full non-training ML workflow from artifacts to backend handoff."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_risk_events import BASE_DIR, DEFAULT_SOURCE_ROOT, build_events, resolve_source_root
from materialize_temporary_artifacts import (
    find_missing_standard_artifacts,
    materialize_artifacts,
)
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
    parser.add_argument(
        "--skip-materialize",
        action="store_true",
        help="Do not auto-copy missing standard artifacts from ml/Temprary/ml.",
    )
    return parser.parse_args()


def prepare_standard_artifacts(
    source_root: Path | None = None,
    skip_materialize: bool = False,
) -> dict | None:
    """Populate the standard ml/ layout from the temporary cache when needed."""
    if source_root is not None:
        return None

    missing_before = find_missing_standard_artifacts(
        target_root=BASE_DIR,
        source_root=DEFAULT_SOURCE_ROOT,
    )
    if not missing_before:
        return {
            "attempted": False,
            "source_root": str(DEFAULT_SOURCE_ROOT.resolve()),
            "target_root": str(BASE_DIR.resolve()),
            "missing_before": [],
            "missing_after": [],
            "reason": "standard_artifacts_present",
        }

    if skip_materialize:
        return {
            "attempted": False,
            "source_root": str(DEFAULT_SOURCE_ROOT.resolve()),
            "target_root": str(BASE_DIR.resolve()),
            "missing_before": missing_before,
            "missing_after": missing_before,
            "reason": "skipped_by_flag",
        }

    summary = materialize_artifacts(
        source_root=DEFAULT_SOURCE_ROOT,
        target_root=BASE_DIR,
        overwrite=False,
    )
    summary["attempted"] = True
    summary["missing_before"] = missing_before
    summary["missing_after"] = find_missing_standard_artifacts(
        target_root=BASE_DIR,
        source_root=DEFAULT_SOURCE_ROOT,
    )
    return summary


def run_workflow(
    source_root: Path | None = None,
    output_dir: Path | None = None,
    backend_data_dir: Path | None = None,
    skip_model_check: bool = False,
    skip_materialize: bool = False,
) -> dict:
    output_dir = (output_dir or BASE_DIR / "outputs").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    backend_data_dir = (backend_data_dir or BASE_DIR.parent / "backend" / "data").resolve()

    materialize_summary = prepare_standard_artifacts(
        source_root=source_root,
        skip_materialize=skip_materialize,
    )
    artifact_summary = inspect_artifacts(source_root)
    data_dir, _ = resolve_source_root(source_root)
    source_root = data_dir.parent

    model_summary = None
    model_path = source_root / "models" / "best.pt"
    if not skip_model_check and model_path.exists():
        model_summary = inspect_model(model_path)

    events, build_metadata = build_events(
        source_root=source_root,
        output_dir=output_dir,
        return_metadata=True,
    )
    risk_events_path = output_dir / "risk_events.json"
    with risk_events_path.open("w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

    source_geojson = data_dir / "bar_reef.geojson"
    risk_dest, geo_dest = sync_outputs(risk_events_path, source_geojson, backend_data_dir)

    gfw_count = sum(1 for event in events if event["source"] == "GFW")
    yolo_count = sum(1 for event in events if event["source"] == "YOLO_SAR")
    bar003 = next((event for event in events if event["id"] == "bar-reef-003"), None)

    workflow_summary = {
        "source_root": str(source_root),
        "materialize_summary": materialize_summary,
        "artifact_summary": artifact_summary,
        "model_summary": model_summary,
        "risk_events_path": str(risk_events_path),
        "backend_risk_events_path": str(risk_dest),
        "backend_geojson_path": str(geo_dest),
        "total_events": len(events),
        "gfw_events": gfw_count,
        "yolo_events": yolo_count,
        "used_fallback_gfw_data": build_metadata["used_fallback_gfw_data"],
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

    workflow_summary["summary_path"] = str(summary_path)
    workflow_summary["total_events"] = len(events)

    return workflow_summary


def main() -> None:
    args = parse_args()
    workflow_summary = run_workflow(
        source_root=args.source_root,
        output_dir=args.output_dir,
        backend_data_dir=args.backend_data_dir,
        skip_model_check=args.skip_model_check,
        skip_materialize=args.skip_materialize,
    )

    if workflow_summary["materialize_summary"]:
        materialize_summary = workflow_summary["materialize_summary"]
        if materialize_summary.get("attempted"):
            print(
                "Materialized missing standard artifacts: "
                f"{len(materialize_summary['copied'])} copied, "
                f"{len(materialize_summary['skipped'])} skipped"
            )

    print(f"Workflow summary written to: {workflow_summary['summary_path']}")
    print(f"Total events: {workflow_summary['total_events']}")
    print(f"GFW events: {workflow_summary['gfw_events']}")
    print(f"YOLO events: {workflow_summary['yolo_events']}")
    print(f"GFW fallback data used: {workflow_summary['used_fallback_gfw_data']}")
    bar003 = workflow_summary["bar_reef_003"]
    if bar003["risk_score"] is not None:
        print(
            "bar-reef-003: "
            f"{bar003['risk_score']} / {bar003['risk_level']} / {bar003['timestamp']}"
        )


if __name__ == "__main__":
    main()
