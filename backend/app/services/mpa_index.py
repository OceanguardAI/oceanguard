"""Multi-MPA spatial index for nearest-protected-area lookups.

Loads a GeoJSON FeatureCollection of marine protected areas (mpas.geojson, from
ml/fetch_wdpa.py) and answers, for any detection coordinate, which MPA it is
inside or nearest to and how far. Falls back to the single Bar Reef polygon when
no multi-MPA file is present, so the system still runs offline.

A shapely STRtree keeps lookups O(log n) even with the full global WDPA set
(~10k polygons), so scoring tens of thousands of detections stays fast.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from shapely import STRtree
from shapely.geometry import Point, box, mapping, shape
from shapely.ops import nearest_points

from app.core.config import settings

# Distance (km) under which a detection counts as "near" an MPA boundary.
NEAR_MPA_KM = 10.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class MPAIndex:
    """Loaded set of MPA polygons with nearest-area lookup."""

    def __init__(self) -> None:
        self._geoms: list[Any] = []
        self._names: list[str] = []
        self._tree: STRtree | None = None
        self._source_path: Path | None = None

    @property
    def count(self) -> int:
        return len(self._geoms)

    @property
    def source(self) -> str | None:
        return self._source_path.name if self._source_path else None

    def _mpa_file(self) -> Path:
        """Prefer the multi-MPA file; fall back to the single Bar Reef polygon."""
        multi = settings.data_dir / "mpas.geojson"
        if multi.exists():
            return multi
        return settings.data_dir / "bar_reef.geojson"

    def load(self) -> None:
        path = self._mpa_file()
        self._geoms, self._names, self._tree = [], [], None
        if not path.exists():
            self._source_path = None
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("type") == "FeatureCollection":
            features = data.get("features", [])
        elif data.get("type") == "Feature":
            features = [data]
        else:  # bare geometry
            features = [{"type": "Feature", "properties": {}, "geometry": data}]

        for feat in features:
            geom = feat.get("geometry")
            if not geom:
                continue
            try:
                g = shape(geom)
            except Exception:
                continue
            if g.is_empty:
                continue
            name = (feat.get("properties") or {}).get("NAME") or "Protected Area"
            self._geoms.append(g)
            self._names.append(name)

        self._tree = STRtree(self._geoms) if self._geoms else None
        self._source_path = path

    def nearest(self, lat: float, lon: float) -> tuple[str | None, float, bool, bool]:
        """Return (mpa_name, distance_km, inside_mpa, near_mpa) for a point.

        Uses an STRtree so each lookup is O(log n) regardless of MPA count.
        distance_km is 0.0 when inside any MPA. When no MPAs are loaded, returns
        (None, inf, False, False) so callers can degrade gracefully.
        """
        if not self._geoms or self._tree is None:
            return None, float("inf"), False, False

        point = Point(lon, lat)

        # 1) Containment: any polygon the point intersects => inside an MPA.
        # STRtree applies the predicate as point.predicate(polygon); use
        # "intersects" (true when the point is within or on a polygon) since a
        # point can never "cover" a polygon.
        covering = self._tree.query(point, predicate="intersects")
        if len(covering) > 0:
            return self._names[int(covering[0])], 0.0, True, False

        # 2) Nearest polygon (planar query), then true distance in km to it.
        nearest_idx = int(self._tree.query_nearest(point)[0])
        geom = self._geoms[nearest_idx]
        # Use the geometry itself (not .boundary): the point is already known to
        # be outside, and some make_valid outputs (Point/GeometryCollection) have
        # an empty boundary, which would break nearest_points.
        near_pt = nearest_points(point, geom)[1]
        dist = round(_haversine_km(lat, lon, near_pt.y, near_pt.x), 2)
        return self._names[nearest_idx], dist, False, (dist <= NEAR_MPA_KM)

    def features_in_bbox(
        self, min_lon: float, min_lat: float, max_lon: float, max_lat: float, limit: int = 800
    ) -> dict[str, Any]:
        """Return a GeoJSON FeatureCollection of MPAs intersecting the bbox.

        Used to serve only the protected areas in the map's current viewport,
        so the frontend never has to render the full global WDPA set at once.
        """
        if not self._geoms or self._tree is None:
            return {"type": "FeatureCollection", "features": []}

        query_box = box(min_lon, min_lat, max_lon, max_lat)
        idxs = self._tree.query(query_box, predicate="intersects")
        features = []
        for i in idxs[:limit]:
            i = int(i)
            features.append(
                {
                    "type": "Feature",
                    "properties": {"NAME": self._names[i]},
                    "geometry": mapping(self._geoms[i]),
                }
            )
        return {"type": "FeatureCollection", "features": features}


# Module-level singleton, loaded lazily on first use.
_index: MPAIndex | None = None


def get_index() -> MPAIndex:
    global _index
    if _index is None:
        _index = MPAIndex()
        _index.load()
    return _index


def reload_index() -> int:
    """Reload the MPA file (e.g. after fetching new WDPA data). Returns count."""
    idx = get_index()
    idx.load()
    return idx.count
