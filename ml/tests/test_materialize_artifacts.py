from pathlib import Path

from materialize_temporary_artifacts import find_missing_standard_artifacts, materialize_artifacts


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_materialize_artifacts_copies_expected_files(tmp_path):
    source_root = tmp_path / "Temprary" / "ml"
    target_root = tmp_path / "workspace_ml"

    _write(source_root / "data" / "bar_reef.geojson", "{}")
    _write(source_root / "data" / "gfw_bar_reef_sar_unmatched.json", "[]")
    _write(source_root / "data" / "overpass_bar_reef_ports.json", "{}")
    _write(source_root / "models" / "best.pt", "weights")
    _write(source_root / "outputs" / "detections_scene1_georef.json", "[]")

    summary = materialize_artifacts(source_root=source_root, target_root=target_root)

    assert len(summary["copied"]) == 5
    assert not summary["skipped"]
    assert (target_root / "data" / "bar_reef.geojson").exists()
    assert (target_root / "models" / "best.pt").exists()
    assert (target_root / "outputs" / "detections_scene1_georef.json").exists()


def test_materialize_artifacts_skips_existing_files_without_overwrite(tmp_path):
    source_root = tmp_path / "Temprary" / "ml"
    target_root = tmp_path / "workspace_ml"

    _write(source_root / "data" / "bar_reef.geojson", "new")
    _write(source_root / "data" / "gfw_bar_reef_sar_unmatched.json", "[]")
    _write(source_root / "data" / "overpass_bar_reef_ports.json", "{}")
    _write(source_root / "models" / "best.pt", "weights")
    _write(source_root / "outputs" / "detections_scene1_georef.json", "[]")
    _write(target_root / "data" / "bar_reef.geojson", "old")

    summary = materialize_artifacts(source_root=source_root, target_root=target_root)

    assert str(target_root / "data" / "bar_reef.geojson") in summary["skipped"]
    assert (target_root / "data" / "bar_reef.geojson").read_text(encoding="utf-8") == "old"


def test_materialize_artifacts_overwrites_when_requested(tmp_path):
    source_root = tmp_path / "Temprary" / "ml"
    target_root = tmp_path / "workspace_ml"

    _write(source_root / "data" / "bar_reef.geojson", "new")
    _write(source_root / "data" / "gfw_bar_reef_sar_unmatched.json", "[]")
    _write(source_root / "data" / "overpass_bar_reef_ports.json", "{}")
    _write(source_root / "models" / "best.pt", "weights")
    _write(source_root / "outputs" / "detections_scene1_georef.json", "[]")
    _write(target_root / "data" / "bar_reef.geojson", "old")

    summary = materialize_artifacts(
        source_root=source_root,
        target_root=target_root,
        overwrite=True,
    )

    assert str(target_root / "data" / "bar_reef.geojson") in summary["copied"]
    assert (target_root / "data" / "bar_reef.geojson").read_text(encoding="utf-8") == "new"


def test_find_missing_standard_artifacts_reports_relative_paths(tmp_path):
    source_root = tmp_path / "Temprary" / "ml"
    target_root = tmp_path / "workspace_ml"

    _write(target_root / "models" / "best.pt", "weights")

    missing = find_missing_standard_artifacts(
        target_root=target_root,
        source_root=source_root,
    )

    assert "data/bar_reef.geojson" in missing
    assert "outputs/detections_scene1_georef.json" in missing
    assert "models/best.pt" not in missing
