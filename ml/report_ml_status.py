"""Summarize ML pipeline readiness, outputs, and backend handoff state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from build_risk_events import DEFAULT_SOURCE_ROOT, resolve_source_root
from validate_artifacts import inspect_artifacts
from validate_model import inspect_model

REQUIRED_EVENT_FIELDS = [
    "id",
    "source",
    "lat",
    "lon",
    "risk_score",
    "risk_level",
    "sar_confidence",
    "image_quality",
    "ais_matched",
    "ais_data_available",
    "matching_method",
    "inside_mpa",
    "near_mpa",
    "mpa_name",
    "distance_to_mpa_km",
    "distance_from_port_km",
    "nearest_port",
    "timestamp",
    "review_status",
    "why_flagged",
    "uncertainty",
    "confidence_threshold",
    "recommended_action",
    "thumbnail",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize ML workflow readiness and outputs.")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="Artifact root containing data/, models/, and outputs/ folders.",
    )
    parser.add_argument(
        "--risk-events-path",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs" / "risk_events.json",
        help="Path to the generated risk_events.json file.",
    )
    parser.add_argument(
        "--backend-data-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "backend" / "data",
        help="Path to backend/data for handoff verification.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="Optional explicit model path. Defaults to <source_root>/models/best.pt when present.",
    )
    parser.add_argument(
        "--as-json",
        action="store_true",
        help="Print the full status report as JSON.",
    )
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_risk_events(risk_events_path: Path) -> dict:
    """Return a compact summary of the generated risk events payload."""
    resolved = risk_events_path.resolve()
    if not resolved.exists():
        return {
            "exists": False,
            "path": str(resolved),
        }

    with resolved.open(encoding="utf-8") as f:
        events = json.load(f)

    if not isinstance(events, list):
        raise ValueError("risk_events.json must contain a JSON list of event objects.")

    source_counts: dict[str, int] = {}
    missing_field_samples: list[dict] = []
    null_risk_event_ids: list[str] = []

    for event in events:
        source = event.get("source", "UNKNOWN")
        source_counts[source] = source_counts.get(source, 0) + 1

        missing = [field for field in REQUIRED_EVENT_FIELDS if field not in event]
        if missing and len(missing_field_samples) < 5:
            missing_field_samples.append({"id": event.get("id"), "missing": missing})

        if event.get("risk_score") is None or event.get("risk_level") is None:
            null_risk_event_ids.append(event.get("id", "unknown"))

    bar003 = next((event for event in events if event.get("id") == "bar-reef-003"), None)

    return {
        "exists": True,
        "path": str(resolved),
        "sha256": _sha256(resolved),
        "total_events": len(events),
        "source_counts": source_counts,
        "missing_field_samples": missing_field_samples,
        "events_with_null_risk": null_risk_event_ids[:10],
        "bar_reef_003": {
            "risk_score": bar003.get("risk_score") if bar003 else None,
            "risk_level": bar003.get("risk_level") if bar003 else None,
            "near_mpa": bar003.get("near_mpa") if bar003 else None,
            "inside_mpa": bar003.get("inside_mpa") if bar003 else None,
            "distance_to_mpa_km": bar003.get("distance_to_mpa_km") if bar003 else None,
            "timestamp": bar003.get("timestamp") if bar003 else None,
        },
    }


def inspect_backend_handoff(
    backend_data_dir: Path,
    expected_risk_events: Path | None = None,
    expected_geojson: Path | None = None,
) -> dict:
    """Check whether backend/data contains the expected ML handoff files."""
    resolved_dir = backend_data_dir.resolve()
    risk_path = resolved_dir / "risk_events.json"
    geo_path = resolved_dir / "bar_reef.geojson"

    summary = {
        "backend_data_dir": str(resolved_dir),
        "risk_events_exists": risk_path.exists(),
        "bar_reef_geojson_exists": geo_path.exists(),
    }

    if risk_path.exists():
        summary["risk_events_sha256"] = _sha256(risk_path)
    if geo_path.exists():
        summary["bar_reef_geojson_sha256"] = _sha256(geo_path)

    if expected_risk_events is not None and expected_risk_events.exists() and risk_path.exists():
        summary["risk_events_matches_ml_output"] = (
            _sha256(expected_risk_events.resolve()) == summary["risk_events_sha256"]
        )

    if expected_geojson is not None and expected_geojson.exists() and geo_path.exists():
        summary["bar_reef_geojson_matches_source"] = (
            _sha256(expected_geojson.resolve()) == summary["bar_reef_geojson_sha256"]
        )

    return summary


def summarize_ml_status(
    source_root: Path | None = None,
    risk_events_path: Path | None = None,
    backend_data_dir: Path | None = None,
    model_path: Path | None = None,
) -> dict:
    """Return a full ML workflow status report."""
    artifact_summary = inspect_artifacts(source_root)
    data_dir, outputs_dir = resolve_source_root(source_root)
    source_root = data_dir.parent

    risk_events_path = (risk_events_path or outputs_dir / "risk_events.json").resolve()
    backend_data_dir = (
        backend_data_dir or Path(__file__).resolve().parent.parent / "backend" / "data"
    ).resolve()
    model_path = (model_path or source_root / "models" / "best.pt").resolve()

    model_summary = None
    if model_path.exists():
        model_summary = inspect_model(model_path)
    else:
        model_summary = {
            "model_path": str(model_path),
            "exists": False,
        }

    risk_events_summary = inspect_risk_events(risk_events_path)
    backend_summary = inspect_backend_handoff(
        backend_data_dir=backend_data_dir,
        expected_risk_events=risk_events_path,
        expected_geojson=data_dir / "bar_reef.geojson",
    )

    return {
        "source_root": str(source_root),
        "artifact_summary": artifact_summary,
        "model_summary": model_summary,
        "risk_events_summary": risk_events_summary,
        "backend_handoff": backend_summary,
        "using_temporary_cache": source_root == DEFAULT_SOURCE_ROOT.resolve(),
    }


def _print_report(report: dict) -> None:
    artifact_summary = report["artifact_summary"]
    model_summary = report["model_summary"]
    risk_events_summary = report["risk_events_summary"]
    backend_summary = report["backend_handoff"]

    print(f"Source root: {report['source_root']}")
    print(f"Using temporary cache: {report['using_temporary_cache']}")
    print(
        "Artifacts: "
        f"GFW={artifact_summary['gfw_detections']}, "
        f"YOLO={artifact_summary['yolo_detections']}, "
        f"ports={artifact_summary['port_elements']}"
    )

    if model_summary and model_summary.get("exists") is False:
        print(f"Model: missing at {model_summary['model_path']}")
    elif model_summary:
        print(
            "Model: "
            f"{model_summary['model_type']} / {model_summary['task']} / "
            f"{model_summary['class_count']} classes"
        )

    if not risk_events_summary["exists"]:
        print(f"risk_events.json: missing at {risk_events_summary['path']}")
    else:
        print(
            "risk_events.json: "
            f"{risk_events_summary['total_events']} events / "
            f"sources={risk_events_summary['source_counts']}"
        )
        bar003 = risk_events_summary["bar_reef_003"]
        if bar003["risk_score"] is not None:
            print(
                "bar-reef-003: "
                f"{bar003['risk_score']} / {bar003['risk_level']} / "
                f"near={bar003['near_mpa']} / inside={bar003['inside_mpa']}"
            )
        if risk_events_summary["missing_field_samples"]:
            print(f"Schema warnings: {len(risk_events_summary['missing_field_samples'])} sampled events")
        if risk_events_summary["events_with_null_risk"]:
            print(
                "Null risk fields found in: "
                f"{risk_events_summary['events_with_null_risk']}"
            )

    print(
        "Backend handoff: "
        f"risk_events={backend_summary['risk_events_exists']} / "
        f"bar_reef_geojson={backend_summary['bar_reef_geojson_exists']}"
    )
    if "risk_events_matches_ml_output" in backend_summary:
        print(f"Backend risk_events matches ML output: {backend_summary['risk_events_matches_ml_output']}")
    if "bar_reef_geojson_matches_source" in backend_summary:
        print(
            "Backend bar_reef.geojson matches source: "
            f"{backend_summary['bar_reef_geojson_matches_source']}"
        )


def main() -> None:
    args = parse_args()
    report = summarize_ml_status(
        source_root=args.source_root,
        risk_events_path=args.risk_events_path,
        backend_data_dir=args.backend_data_dir,
        model_path=args.model_path,
    )

    if args.as_json:
        print(json.dumps(report, indent=2))
        return

    _print_report(report)


if __name__ == "__main__":
    main()
