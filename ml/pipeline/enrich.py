"""MPA distance, port distance, and spatial classification."""
from __future__ import annotations
import json
import math
from shapely.geometry import shape, Point
from shapely.ops import nearest_points


def load_mpa(geojson_path: str):
    """Load Bar Reef MPA polygon. Returns shapely geometry."""
    with open(geojson_path) as f:
        data = json.load(f)
    if data["type"] == "Feature":
        return shape(data["geometry"])
    elif data["type"] == "FeatureCollection":
        return shape(data["features"][0]["geometry"])
    else:
        return shape(data)  # bare geometry


def distance_to_mpa(lat: float, lon: float, mpa_polygon) -> float:
    """Geodesic distance in km from point to nearest MPA boundary.
    Returns 0.0 if the point is inside the MPA."""
    point = Point(lon, lat)  # shapely uses (lon, lat) = (x, y)
    if mpa_polygon.contains(point):
        return 0.0
    nearest = nearest_points(point, mpa_polygon.boundary)[1]
    return round(_haversine(lat, lon, nearest.y, nearest.x), 2)


def classify_mpa(distance_km: float) -> tuple[bool, bool]:
    """Return (inside_mpa, near_mpa).
    inside_mpa: distance == 0
    near_mpa:   distance > 0 and distance <= 5.0 km
    """
    inside = distance_km == 0.0
    near = (not inside) and distance_km <= 5.0
    return inside, near


def nearest_port_distance(lat: float, lon: float, ports_json_path: str) -> tuple[float, str]:
    """Return (distance_km, port_name) for the nearest OSM port."""
    with open(ports_json_path) as f:
        data = json.load(f)

    elements = data.get("elements", [])
    if not elements:
        # fallback: known marina coordinates
        return round(_haversine(lat, lon, 8.2155202, 79.7061466), 1), "Marina (OSM)"

    best_dist = float("inf")
    best_name = "Port (OSM)"
    for el in elements:
        if "lat" not in el or "lon" not in el:
            continue
        d = _haversine(lat, lon, el["lat"], el["lon"])
        if d < best_dist:
            best_dist = d
            tags = el.get("tags", {})
            best_name = tags.get("name", tags.get("leisure", "Port (OSM)"))

    return round(best_dist, 1), best_name


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


if __name__ == "__main__":
    mpa = load_mpa("data/bar_reef.geojson")
    # Test: bar-reef-003 should be ~0.4 km from MPA
    d = distance_to_mpa(8.51, 79.68, mpa)
    inside, near = classify_mpa(d)
    print(f"bar-reef-003: {d:.2f} km, inside={inside}, near={near}")
    assert near is True, f"Expected near=True, got {near}"
    # Test: bar-reef-001 should be ~14 km
    d2 = distance_to_mpa(8.66, 79.75, mpa)
    print(f"bar-reef-001: {d2:.2f} km")
    assert d2 > 5.0, f"Expected >5km, got {d2}"
    print("enrich.py smoke test PASSED")
