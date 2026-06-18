"""Multi-MPA spatial index for nearest-protected-area lookups.

Loads a GeoJSON FeatureCollection of marine protected areas (mpas.geojson, from
ml/fetch_wdpa.py) and answers, for any detection coordinate, which MPA it is
inside or nearest to and how far. Falls back to the single Bar Reef polygon when
no multi-MPA file is present, so the system still runs offline.

A cheap bounding-box prefilter keeps lookups fast even with thousands of MPAs:
only polygons whose bbox is within a search margin are tested with shapely.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from shapely.geometry import Point, shape
from shapely.ops import nearest_points

from app.core.config import settings

# Distance (km) under which a detection counts as "near" an MPA boundary.
NEAR_MPA_KM = 10.0
# bbox prefilter half-window in degrees (~110 km) — only test nearby polygons.
_PREFILTER_DEG = 1.0


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
        self._bboxes: list[tuple[float, float, float, float]] = []  # (minx,miny,maxx,maxy)
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
        self._geoms, self._names, self._bboxes = [], [], []
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
            self._bboxes.append(g.bounds)

        self._source_path = path

    def nearest(self, lat: float, lon: float) -> tuple[str | None, float, bool, bool]:
        """Return (mpa_name, distance_km, inside_mpa, near_mpa) for a point.

        distance_km is 0.0 when inside any MPA. When no MPAs are loaded, returns
        (None, inf, False, False) so callers can degrade gracefully.
        """
        if not self._geoms:
            return None, float("inf"), False, False

        point = Point(lon, lat)

        # 1) Containment check (only polygons whose bbox contains the point).
        for i, (minx, miny, maxx, maxy) in enumerate(self._bboxes):
            if minx <= lon <= maxx and miny <= lat <= maxy and self._geoms[i].contains(point):
                return self._names[i], 0.0, True, False

        # 2) Nearest boundary among polygons within the prefilter window.
        best_name: str | None = None
        best_dist = float("inf")
        for i, (minx, miny, maxx, maxy) in enumerate(self._bboxes):
            if (
                lon < minx - _PREFILTER_DEG or lon > maxx + _PREFILTER_DEG
                or lat < miny - _PREFILTER_DEG or lat > maxy + _PREFILTER_DEG
            ):
                continue
            near_pt = nearest_points(point, self._geoms[i].boundary)[1]
            dist = _haversine_km(lat, lon, near_pt.y, near_pt.x)
            if dist < best_dist:
                best_dist, best_name = dist, self._names[i]

        if best_name is None:  # nothing in window — fall back to a coarse scan
            for i, g in enumerate(self._geoms):
                near_pt = nearest_points(point, g.boundary)[1]
                dist = _haversine_km(lat, lon, near_pt.y, near_pt.x)
                if dist < best_dist:
                    best_dist, best_name = dist, self._names[i]

        best_dist = round(best_dist, 2)
        return best_name, best_dist, False, (best_dist <= NEAR_MPA_KM)


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
