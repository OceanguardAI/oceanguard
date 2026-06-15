"""Convert detection pixel locations to WGS84 latitude/longitude."""
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
    """Add `lat` and `lon` values to each detection dictionary."""
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)

    for detection in detections:
        utm_x = geo_transform_x + (detection["col_off"] + detection["x_center_px"]) * pixel_size
        utm_y = geo_transform_y - (detection["row_off"] + detection["y_center_px"]) * pixel_size
        lon, lat = transformer.transform(utm_x, utm_y)
        detection["lon"] = round(lon, 6)
        detection["lat"] = round(lat, 6)

    return detections


if __name__ == "__main__":
    test = [{"col_off": 0, "row_off": 0, "x_center_px": 0, "y_center_px": 0}]
    result = georeference_detections(test)
    print(f"Origin: lat={result[0]['lat']}, lon={result[0]['lon']}")
