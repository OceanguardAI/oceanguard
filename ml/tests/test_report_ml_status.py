from __future__ import annotations

import json
from pathlib import Path

import report_ml_status as reporter


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_inspect_risk_events_summarizes_schema_and_counts(tmp_path):
    risk_events_path = tmp_path / "risk_events.json"
    _write_json(
        risk_events_path,
        [
            {
                "id": "bar-reef-003",
                "source": "GFW",
                "lat": 8.51,
                "lon": 79.68,
                "risk_score": 0.61,
                "risk_level": "HIGH",
                "sar_confidence": 0.70,
                "image_quality": "Good",
                "ais_matched": False,
                "ais_data_available": True,
                "matching_method": "Spatial 2km + 3hr time window",
                "inside_mpa": False,
                "near_mpa": True,
                "mpa_name": "Bar Reef Marine Sanctuary",
                "distance_to_mpa_km": 0.4,
                "distance_from_port_km": 33.0,
                "nearest_port": "Marina (OSM)",
                "timestamp": "2026-06-09T14:32:00Z",
                "review_status": "Pending",
                "why_flagged": "",
                "uncertainty": "",
                "confidence_threshold": 0.45,
                "recommended_action": "Review",
                "thumbnail": None,
            },
            {
                "id": "yolo-001",
                "source": "YOLO_SAR",
                "lat": 7.23,
                "lon": 4.56,
                "risk_score": None,
                "risk_level": None,
            },
        ],
    )

    summary = reporter.inspect_risk_events(risk_events_path)

    assert summary["exists"] is True
    assert summary["total_events"] == 2
    assert summary["source_counts"] == {"GFW": 1, "YOLO_SAR": 1}
    assert summary["bar_reef_003"]["risk_score"] == 0.61
    assert summary["events_with_null_risk"] == ["yolo-001"]
    assert summary["missing_field_samples"][0]["id"] == "yolo-001"


def test_summarize_ml_status_reports_backend_match_and_missing_model(tmp_path):
    source_root = tmp_path / "ml"
    backend_dir = tmp_path / "backend" / "data"

    _write_json(
        source_root / "data" / "bar_reef.geojson",
        {
            "type": "Feature",
            "properties": {"NAME": "Bar Reef Marine Sanctuary"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [79.73550022, 8.26746323],
                        [79.76349894, 8.32294782],
                        [79.78222715, 8.53409068],
                        [79.68343578, 8.53142862],
                        [79.68286497, 8.26487243],
                        [79.73550022, 8.26746323],
                    ]
                ],
            },
        },
    )
    _write_json(
        source_root / "data" / "gfw_bar_reef_sar_unmatched.json",
        {"entries": [{"id": "bar-reef-003", "lat": 8.51, "lon": 79.68}]},
    )
    _write_json(
        source_root / "data" / "overpass_bar_reef_ports.json",
        {"elements": [{"lat": 8.2155202, "lon": 79.7061466, "tags": {"name": "Marina (OSM)"}}]},
    )
    _write_json(
        source_root / "outputs" / "detections_scene1_georef.json",
        [{"lat": 7.23, "lon": 4.56, "confidence": 0.76}],
    )
    _write_json(
        source_root / "outputs" / "risk_events.json",
        [
            {
                "id": "bar-reef-003",
                "source": "GFW",
                "lat": 8.51,
                "lon": 79.68,
                "risk_score": 0.61,
                "risk_level": "HIGH",
                "sar_confidence": 0.70,
                "image_quality": "Good",
                "ais_matched": False,
                "ais_data_available": True,
                "matching_method": "Spatial 2km + 3hr time window",
                "inside_mpa": False,
                "near_mpa": True,
                "mpa_name": "Bar Reef Marine Sanctuary",
                "distance_to_mpa_km": 0.4,
                "distance_from_port_km": 33.0,
                "nearest_port": "Marina (OSM)",
                "timestamp": "2026-06-09T14:32:00Z",
                "review_status": "Pending",
                "why_flagged": "",
                "uncertainty": "",
                "confidence_threshold": 0.45,
                "recommended_action": "Review",
                "thumbnail": None,
            }
        ],
    )

    (backend_dir).mkdir(parents=True, exist_ok=True)
    (backend_dir / "risk_events.json").write_bytes((source_root / "outputs" / "risk_events.json").read_bytes())
    (backend_dir / "bar_reef.geojson").write_bytes((source_root / "data" / "bar_reef.geojson").read_bytes())

    report = reporter.summarize_ml_status(
        source_root=source_root,
        risk_events_path=source_root / "outputs" / "risk_events.json",
        backend_data_dir=backend_dir,
    )

    assert report["source_root"] == str(source_root.resolve())
    assert report["model_summary"]["exists"] is False
    assert report["risk_events_summary"]["total_events"] == 1
    assert report["backend_handoff"]["risk_events_matches_ml_output"] is True
    assert report["backend_handoff"]["bar_reef_geojson_matches_source"] is True
