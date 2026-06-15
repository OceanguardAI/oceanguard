"""MPA distance, port distance, and spatial classification helpers."""
from __future__ import annotations

import json
import math
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import nearest_points


def load_mpa(geojson_path: str | Path):
    """Load an MPA polygon from GeoJSON and return a shapely geometry."""
    with Path(geojson_path).open(encoding="utf-8") as f:
        data = json.load(f)

    if data["type"] == "Feature":
        return shape(data["geometry"])
    if data["type"] == "FeatureCollection":
        return shape(data["features"][0]["geometry"])
    return shape(data)


def distance_to_mpa(lat: float, lon: float, mpa_polygon) -> float:
    """Return km from point to nearest MPA boundary, or 0.0 when inside."""
    point = Point(lon, lat)
    if mpa_polygon.contains(point):
        return 0.0

    nearest = nearest_points(point, mpa_polygon.boundary)[1]
    return round(_haversine(lat, lon, nearest.y, nearest.x), 2)


def classify_mpa(distance_km: float) -> tuple[bool, bool]:
    """Return `(inside_mpa, near_mpa)` from a distance-to-boundary value."""
    inside = distance_km == 0.0
    near = (not inside) and distance_km <= 5.0
    return inside, near


def nearest_port_distance(lat: float, lon: float, ports_json_path: str | Path) -> tuple[float, str]:
    """Return distance in km and name for the nearest OSM port node."""
    with Path(ports_json_path).open(encoding="utf-8") as f:
        data = json.load(f)

    elements = data.get("elements", [])
    if not elements:
        return round(_haversine(lat, lon, 8.2155202, 79.7061466), 1), "Marina (OSM)"

    best_dist = float("inf")
    best_name = "Port (OSM)"

    for element in elements:
        if "lat" not in element or "lon" not in element:
            continue

        distance = _haversine(lat, lon, element["lat"], element["lon"])
        if distance < best_dist:
            best_dist = distance
            tags = element.get("tags", {})
            best_name = tags.get("name", tags.get("leisure", "Port (OSM)"))

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
