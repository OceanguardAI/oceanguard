from pathlib import Path

import pytest

from pipeline.georeference import georeference_detections
from pipeline.tiling import tile_sar


def test_georeference_detections_adds_wgs84_coordinates():
    pytest.importorskip("pyproj")

    detections = [{"col_off": 0, "row_off": 0, "x_center_px": 0.0, "y_center_px": 0.0}]

    result = georeference_detections(detections)

    assert result[0]["lat"] == 7.17938
    assert result[0]["lon"] == 2.792233


def test_tile_sar_writes_padded_tiles_and_skips_sparse_windows(tmp_path):
    np = pytest.importorskip("numpy")
    rasterio = pytest.importorskip("rasterio")
    pytest.importorskip("PIL")
    from PIL import Image
    from rasterio.transform import from_origin

    tif_path = tmp_path / "sample.tif"
    tiles_dir = tmp_path / "tiles"
    data = np.array(
        [
            [-10, -20, -32768],
            [-5, -15, -32768],
            [-30, -40, -12],
        ],
        dtype="float32",
    )

    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        nodata=-32768,
        transform=from_origin(1000, 1000, 10, 10),
    ) as dataset:
        dataset.write(data, 1)

    results = tile_sar(
        str(tif_path),
        str(tiles_dir),
        tile_size=2,
        min_valid_frac=0.5,
    )

    assert len(results) == 3
    assert [Path(tile_path).name for _, _, tile_path in results] == [
        "tile_r0000_c0000.png",
        "tile_r0002_c0000.png",
        "tile_r0002_c0002.png",
    ]

    edge_tile = Image.open(tiles_dir / "tile_r0002_c0002.png")
    assert edge_tile.size == (2, 2)
