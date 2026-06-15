import json

from sync_outputs_to_backend import sync_outputs
from validate_artifacts import inspect_artifacts


def test_sync_outputs_copies_both_files(tmp_path):
    risk_events = tmp_path / "risk_events.json"
    bar_reef = tmp_path / "bar_reef.geojson"
    backend_data = tmp_path / "backend" / "data"

    risk_events.write_text(json.dumps([{"id": "x"}]), encoding="utf-8")
    bar_reef.write_text(json.dumps({"type": "Feature"}), encoding="utf-8")

    risk_dest, geo_dest = sync_outputs(risk_events, bar_reef, backend_data)

    assert risk_dest.exists()
    assert geo_dest.exists()
    assert json.loads(risk_dest.read_text(encoding="utf-8")) == [{"id": "x"}]
    assert json.loads(geo_dest.read_text(encoding="utf-8")) == {"type": "Feature"}


def test_inspect_artifacts_returns_summary(tmp_path):
    source_root = tmp_path / "Temprary" / "ml"
    data_dir = source_root / "data"
    outputs_dir = source_root / "outputs"
    data_dir.mkdir(parents=True)
    outputs_dir.mkdir(parents=True)

    (data_dir / "bar_reef.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": [{"geometry": {"type": "Polygon", "coordinates": [[[79.7, 8.2], [79.8, 8.3], [79.7, 8.2]]]}, "properties": {}}]}),
        encoding="utf-8",
    )
    (data_dir / "gfw_bar_reef_sar_unmatched.json").write_text(
        json.dumps({"detections": [{"id": "bar-reef-003", "lat": 8.51, "lon": 79.68}]}),
        encoding="utf-8",
    )
    (data_dir / "overpass_bar_reef_ports.json").write_text(
        json.dumps({"elements": [{"lat": 8.2, "lon": 79.7, "tags": {"name": "Marina"}}]}),
        encoding="utf-8",
    )
    (outputs_dir / "detections_scene1_georef.json").write_text(
        json.dumps([{"lat": 7.23, "lon": 4.56, "confidence": 0.76}]),
        encoding="utf-8",
    )

    summary = inspect_artifacts(source_root)

    assert summary["gfw_detections"] == 1
    assert summary["port_elements"] == 1
    assert summary["geojson_type"] == "FeatureCollection"
    assert summary["yolo_detections"] == 1
