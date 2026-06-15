from pathlib import Path

from pipeline.detect import _parse_offsets


def test_detect_helpers_import_without_yolo_stack() -> None:
    row_off, col_off = _parse_offsets("tiles/tile_r0640_c1280.png")
    assert row_off == 640
    assert col_off == 1280


def test_georeference_module_imports_without_pyproj() -> None:
    module_path = Path("ml/pipeline/georeference.py")
    assert module_path.exists()
