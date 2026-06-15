"""Tile a large SAR GeoTIFF into 640x640 PNGs for YOLO inference."""
from __future__ import annotations

import os

import numpy as np
import rasterio
from PIL import Image
from rasterio.windows import Window


def tile_sar(
    tif_path: str,
    output_dir: str,
    tile_size: int = 640,
    db_min: float = -50.0,
    db_max: float = 0.0,
    nodata: float = -32768,
    min_valid_frac: float = 0.50,
) -> list[tuple[int, int, str]]:
    """Return `(row_off, col_off, tile_path)` entries for written tiles."""
    os.makedirs(output_dir, exist_ok=True)
    results: list[tuple[int, int, str]] = []
    skipped = 0

    with rasterio.open(tif_path) as src:
        width, height = src.width, src.height
        rows = range(0, height, tile_size)
        cols = range(0, width, tile_size)

        for row_off in rows:
            for col_off in cols:
                tile_height = min(tile_size, height - row_off)
                tile_width = min(tile_size, width - col_off)

                window = Window(col_off, row_off, tile_width, tile_height)
                data = src.read(1, window=window).astype(float)

                valid_mask = data != nodata
                valid_frac = valid_mask.sum() / data.size
                if valid_frac < min_valid_frac:
                    skipped += 1
                    continue

                data[~valid_mask] = db_min
                normalized = np.clip((data - db_min) / (db_max - db_min) * 255, 0, 255).astype(
                    np.uint8
                )

                if tile_height < tile_size or tile_width < tile_size:
                    padded = np.zeros((tile_size, tile_size), dtype=np.uint8)
                    padded[:tile_height, :tile_width] = normalized
                    normalized = padded

                tile_path = os.path.join(output_dir, f"tile_r{row_off:04d}_c{col_off:04d}.png")
                Image.fromarray(normalized).save(tile_path)
                results.append((row_off, col_off, tile_path))

    print(f"Tiling complete: {len(results)} written, {skipped} skipped")
    return results


if __name__ == "__main__":
    import sys

    tif = sys.argv[1] if len(sys.argv) > 1 else "data/VH_dB.tif"
    tiles = tile_sar(tif, "tiles/")
    if tiles:
        print(f"First tile: {tiles[0]}")
