import json

import build_risk_events as builder
import run_full_ml_workflow as workflow


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_run_workflow_materializes_standard_artifacts_from_temporary_cache(tmp_path, monkeypatch):
    standard_root = tmp_path / "ml"
    temporary_root = tmp_path / "Temprary" / "ml"
    output_dir = tmp_path / "generated"
    backend_dir = tmp_path / "backend" / "data"

    _write_json(
        temporary_root / "data" / "bar_reef.geojson",
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
        temporary_root / "data" / "gfw_bar_reef_sar_unmatched.json",
        {"entries": builder.DEFAULT_GFW_ENTRIES},
    )
    _write_json(
        temporary_root / "data" / "overpass_bar_reef_ports.json",
        {
            "elements": [
                {
                    "lat": 8.2155202,
                    "lon": 79.7061466,
                    "tags": {"name": "Marina (OSM)"},
                }
            ]
        },
    )
    (temporary_root / "models").mkdir(parents=True, exist_ok=True)
    (temporary_root / "models" / "best.pt").write_text("weights", encoding="utf-8")
    _write_json(
        temporary_root / "outputs" / "detections_scene1_georef.json",
        [{"lat": 7.23, "lon": 4.56, "confidence": 0.76}],
    )

    monkeypatch.setattr(workflow, "BASE_DIR", standard_root)
    monkeypatch.setattr(workflow, "DEFAULT_SOURCE_ROOT", temporary_root)
    monkeypatch.setattr(builder, "BASE_DIR", standard_root)
    monkeypatch.setattr(builder, "DATA_DIR", standard_root / "data")
    monkeypatch.setattr(builder, "OUTPUTS_DIR", standard_root / "outputs")
    monkeypatch.setattr(builder, "DEFAULT_SOURCE_ROOT", temporary_root)

    summary = workflow.run_workflow(
        output_dir=output_dir,
        backend_data_dir=backend_dir,
        skip_model_check=True,
    )

    assert summary["materialize_summary"]["attempted"] is True
    assert len(summary["materialize_summary"]["copied"]) == 5
    assert summary["materialize_summary"]["missing_after"] == []
    assert summary["artifact_summary"]["data_dir"] == str(standard_root / "data")
    assert summary["total_events"] == 5
    assert (standard_root / "models" / "best.pt").exists()
    assert (backend_dir / "risk_events.json").exists()
    assert (backend_dir / "bar_reef.geojson").exists()

    saved_summary = json.loads((output_dir / "ml_workflow_summary.json").read_text(encoding="utf-8"))
    assert saved_summary["materialize_summary"]["attempted"] is True
    assert saved_summary["gfw_events"] == 4
    assert saved_summary["yolo_events"] == 1
    assert saved_summary["used_fallback_gfw_data"] is False
