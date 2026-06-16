"""MPA distance, port distance, and spatial classification helpers."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

try:
    from shapely.geometry import Point, shape
    from shapely.ops import nearest_points
except ImportError:  # pragma: no cover - exercised via fallback path in test envs
    Point = None
    shape = None
    nearest_points = None


def load_mpa(geojson_path: str | Path):
    """Load an MPA polygon from GeoJSON."""
    with Path(geojson_path).open(encoding="utf-8") as f:
        data = json.load(f)

    geometry = data["geometry"] if data["type"] == "Feature" else data
    if data["type"] == "FeatureCollection":
        geometry = data["features"][0]["geometry"]

    if shape is not None:
        return shape(geometry)

    if geometry["type"] != "Polygon":
        raise ValueError("Fallback geometry loader currently supports Polygon only.")
    return {"type": "Polygon", "coordinates": geometry["coordinates"][0]}


def distance_to_mpa(lat: float, lon: float, mpa_polygon: Any) -> float:
    """Return km from point to nearest MPA boundary, or 0.0 when inside."""
    if Point is not None and nearest_points is not None and hasattr(mpa_polygon, "contains"):
        point = Point(lon, lat)
        if mpa_polygon.contains(point):
            return 0.0

        nearest = nearest_points(point, mpa_polygon.boundary)[1]
        return round(_haversine(lat, lon, nearest.y, nearest.x), 2)

    polygon = mpa_polygon["coordinates"]
    if _point_in_polygon(lon, lat, polygon):
        return 0.0

    nearest_lat, nearest_lon = _nearest_point_on_polygon(lat, lon, polygon)
    return round(_haversine(lat, lon, nearest_lat, nearest_lon), 2)


def classify_mpa(distance_km: float) -> tuple[bool, bool]:
    """Return `(inside_mpa, near_mpa)` from a distance-to-boundary value."""
    inside = distance_km == 0.0
    near = (not inside) and distance_km <= 5.0
    return inside, near


def nearest_port_distance(
    lat: float,
    lon: float,
    ports_json_path: str | Path,
) -> tuple[float | None, str | None]:
    """Return distance in km and name for the nearest OSM port node."""
    with Path(ports_json_path).open(encoding="utf-8") as f:
        data = json.load(f)

    elements = data.get("elements", [])
    if not elements:
        return None, None

    best_dist = float("inf")
    best_name: str | None = "Port (OSM)"

    for element in elements:
        if "lat" not in element or "lon" not in element:
            continue

        distance = _haversine(lat, lon, element["lat"], element["lon"])
        if distance < best_dist:
            best_dist = distance
            tags = element.get("tags", {})
            best_name = tags.get("name", tags.get("leisure", "Port (OSM)"))

    if best_dist == float("inf"):
        return None, None

    return round(best_dist, 1), best_name


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two WGS84 coordinates."""
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return radius_km * 2 * math.asin(math.sqrt(a))


def _point_in_polygon(lon: float, lat: float, polygon: list[list[float]]) -> bool:
    inside = False
    j = len(polygon) - 1

    for i, (lon_i, lat_i) in enumerate(polygon):
        lon_j, lat_j = polygon[j]
        intersects = ((lat_i > lat) != (lat_j > lat)) and (
            lon < (lon_j - lon_i) * (lat - lat_i) / ((lat_j - lat_i) or 1e-12) + lon_i
        )
        if intersects:
            inside = not inside
        j = i

    return inside


def _nearest_point_on_polygon(
    lat: float,
    lon: float,
    polygon: list[list[float]],
) -> tuple[float, float]:
    lat_scale = 111.32
    lon_scale = 111.32 * math.cos(math.radians(lat))

    px = lon * lon_scale
    py = lat * lat_scale
    best_distance = float("inf")
    best_point = (lat, lon)

    for start, end in zip(polygon, polygon[1:]):
        x1, y1 = start[0] * lon_scale, start[1] * lat_scale
        x2, y2 = end[0] * lon_scale, end[1] * lat_scale
        projected_x, projected_y = _project_point_to_segment(px, py, x1, y1, x2, y2)
        distance = math.hypot(px - projected_x, py - projected_y)
        if distance < best_distance:
            best_distance = distance
            best_point = (projected_y / lat_scale, projected_x / lon_scale)

    return best_point


def _project_point_to_segment(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> tuple[float, float]:
    dx = x2 - x1
    dy = y2 - y1
    segment_length_sq = dx * dx + dy * dy
    if segment_length_sq == 0:
        return x1, y1

    t = ((px - x1) * dx + (py - y1) * dy) / segment_length_sq
    t = max(0.0, min(1.0, t))
    return x1 + t * dx, y1 + t * dy


if __name__ == "__main__":
    mpa = load_mpa("data/bar_reef.geojson")

    distance = distance_to_mpa(8.51, 79.68, mpa)
    inside, near = classify_mpa(distance)
    print(f"bar-reef-003: {distance:.2f} km, inside={inside}, near={near}")
    assert near is True, f"Expected near=True, got {near}"

    distance_far = distance_to_mpa(8.66, 79.75, mpa)
    print(f"bar-reef-001: {distance_far:.2f} km")
    assert distance_far > 5.0, f"Expected > 5km, got {distance_far}"
    print("enrich.py smoke test PASSED")
