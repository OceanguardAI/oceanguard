import importlib.util
import sys
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from pipeline.detect import _parse_offsets


def test_detect_helpers_import_without_yolo_stack() -> None:
    row_off, col_off = _parse_offsets("tiles/tile_r0640_c1280.png")
    assert row_off == 640
    assert col_off == 1280


def test_georeference_module_imports_without_pyproj() -> None:
    module_path = ML_ROOT / "pipeline" / "georeference.py"
    spec = importlib.util.spec_from_file_location("pipeline.georeference_optional", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "georeference_detections")
