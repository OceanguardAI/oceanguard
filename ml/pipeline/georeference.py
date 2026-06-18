"""Convert detection pixel locations to WGS84 latitude/longitude."""
from __future__ import annotations


def georeference_detections(
    detections: list[dict],
    geo_transform_x: float = 477060.79,
    geo_transform_y: float = 793583.94,
    pixel_size: float = 10.0,
    src_crs: str = "EPSG:32631",
    dst_crs: str = "EPSG:4326",
) -> list[dict]:
    """Add `lat` and `lon` values to each detection dictionary."""
    try:
        from pyproj import Transformer
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise ImportError(
            "pyproj is required for georeference_detections(). Install ml/requirements.txt first."
        ) from exc

    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)

    for detection in detections:
        utm_x = geo_transform_x + (detection["col_off"] + detection["x_center_px"]) * pixel_size
        utm_y = geo_transform_y - (detection["row_off"] + detection["y_center_px"]) * pixel_size
        lon, lat = transformer.transform(utm_x, utm_y)
        detection["lon"] = round(lon, 6)
        detection["lat"] = round(lat, 6)

    return detections


def georeference_from_tif(detections: list[dict], tif_path: str) -> list[dict]:
    """Add `lat`/`lon` using the source GeoTIFF's own CRS and affine transform.

    Unlike georeference_detections(), this reads the real geotransform from a
    live Sentinel-1 tile, so it works for any scene rather than one fixed demo.
    """
    try:
        import rasterio
        from pyproj import Transformer
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise ImportError(
            "rasterio and pyproj are required for georeference_from_tif(). Install ml/requirements.txt first."
        ) from exc

    with rasterio.open(tif_path) as src:
        transform = src.transform
        src_crs = src.crs

    to_wgs84 = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
    for detection in detections:
        px_col = detection["col_off"] + detection["x_center_px"]
        px_row = detection["row_off"] + detection["y_center_px"]
        map_x, map_y = transform * (px_col, px_row)  # pixel -> CRS coordinates
        lon, lat = to_wgs84.transform(map_x, map_y)
        detection["lon"] = round(lon, 6)
        detection["lat"] = round(lat, 6)

    return detections


if __name__ == "__main__":
    test = [{"col_off": 0, "row_off": 0, "x_center_px": 0, "y_center_px": 0}]
    result = georeference_detections(test)
    print(f"Origin: lat={result[0]['lat']}, lon={result[0]['lon']}")
