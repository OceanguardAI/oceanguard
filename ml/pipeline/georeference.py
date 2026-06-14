"""Convert tile pixel coordinates to WGS84 lat/lon."""
from __future__ import annotations
from pyproj import Transformer


def georeference_detections(
    detections: list[dict],
    geo_transform_x: float = 477060.79,
    geo_transform_y: float = 793583.94,
    pixel_size: float = 10.0,
    src_crs: str = "EPSG:32631",
    dst_crs: str = "EPSG:4326",
) -> list[dict]:
    """
    Adds 'lat' and 'lon' to each detection dict. Returns updated list.

    Formula:
        utm_x = geo_transform_x + (col_off + x_center_px) * pixel_size
        utm_y = geo_transform_y - (row_off + y_center_px) * pixel_size
        lon, lat = transform(utm_x, utm_y)

    The xView3 scene (590dd08f71056cacv) is EPSG:32631 (UTM zone 31N).
    Origin: x=477060.79, y=793583.94 (upper-left corner of the image).
    Pixel size: 10 m.
    """
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)

    for det in detections:
        utm_x = geo_transform_x + (det["col_off"] + det["x_center_px"]) * pixel_size
        utm_y = geo_transform_y - (det["row_off"] + det["y_center_px"]) * pixel_size
        lon, lat = transformer.transform(utm_x, utm_y)
        det["lon"] = round(lon, 6)
        det["lat"] = round(lat, 6)

    return detections


if __name__ == "__main__":
    # Smoke test: a detection at tile origin should georef near scene origin
    test = [{"col_off": 0, "row_off": 0, "x_center_px": 0, "y_center_px": 0}]
    result = georeference_detections(test)
    print(f"Origin: lat={result[0]['lat']}, lon={result[0]['lon']}")
    # Should be approximately lat=7.17, lon=4.31 (Gulf of Guinea)
