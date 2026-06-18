"""Fetch marine Protected Areas from the WDPA (World Database on Protected Areas).

Source: the public UNEP-WCMC WDPA feature service on ArcGIS Online. It is open
(no token) and serves the latest WDPA polygons as GeoJSON. We keep only marine
sites (reported marine area > 0) and normalize each feature's properties to a
small, stable schema the backend understands.

  - global:  ~10,800 marine MPAs   ->  large file (tens of MB)
  - regional: pass --bbox to fetch only an area of interest (recommended)

The output is a GeoJSON FeatureCollection written to backend/data/mpas.geojson
by default, which the backend serves at /mpa and uses for nearest-MPA scoring.

Examples
--------
  # Sri Lanka + surrounding Indian Ocean (the monitored region):
  python fetch_wdpa.py --bbox 78.0 5.5 82.5 10.0

  # Every marine MPA on Earth (large download):
  python fetch_wdpa.py --global --out ../backend/data/mpas.world.geojson
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

# UNEP-WCMC WDPA "WDPA_poly_Latest" layer (open, no token).
WDPA_QUERY_URL = (
    "https://services5.arcgis.com/Mj0hjvkNtV7NRhA7/arcgis/rest/services"
    "/WDPA_v0/FeatureServer/1/query"
)
PAGE_SIZE = 1000  # server maxRecordCount is 2000; 1000 keeps responses light
# Marine sites only: reported marine area greater than zero.
MARINE_WHERE = "rep_m_area>0"

BACKEND_DATA = Path(__file__).resolve().parents[1] / "backend" / "data"


def _normalize(feature: dict) -> dict:
    """Reduce a raw WDPA feature to the stable schema the backend expects."""
    p = feature.get("properties", {}) or {}
    name = p.get("name_eng") or p.get("name") or "Unnamed Protected Area"
    return {
        "type": "Feature",
        "properties": {
            "NAME": name,
            "designation": p.get("desig_eng"),
            "iucn_cat": p.get("iucn_cat"),
            "iso3": p.get("iso3"),
            "marine_area_km2": p.get("rep_m_area"),
            "wdpa_id": p.get("site_id"),
            "status": p.get("status"),
        },
        "geometry": feature.get("geometry"),
    }


def _build_params(where: str, offset: int, bbox: list[float] | None) -> dict:
    params = {
        "where": where,
        "outFields": "site_id,name,name_eng,desig_eng,iucn_cat,iso3,rep_m_area,status",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "orderByFields": "site_id",
    }
    if bbox is not None:
        min_lon, min_lat, max_lon, max_lat = bbox
        params.update(
            {
                "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
                "geometryType": "esriGeometryEnvelope",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
            }
        )
    return params


def fetch_wdpa_marine(bbox: list[float] | None, out_path: Path, simplify: bool = False) -> Path:
    """Download marine WDPA polygons (optionally clipped to bbox) as GeoJSON."""
    features: list[dict] = []
    offset = 0
    page = 0

    while True:
        params = _build_params(MARINE_WHERE, offset, bbox)
        if simplify:
            # Server-side generalization: ~0.005 deg (~500 m) cuts file size a lot.
            params["geometryPrecision"] = "4"
        resp = requests.get(WDPA_QUERY_URL, params=params, timeout=180)
        resp.raise_for_status()
        payload = resp.json()
        batch = payload.get("features", [])
        if not batch:
            break

        features.extend(_normalize(f) for f in batch if f.get("geometry"))
        page += 1
        print(f"  page {page}: +{len(batch)} features (total {len(features)})")

        # ArcGIS signals more pages via exceededTransferLimit; also stop on short page.
        if not payload.get("properties", {}).get("exceededTransferLimit") and len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    collection = {"type": "FeatureCollection", "features": features}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(collection), encoding="utf-8")
    size_mb = out_path.stat().st_size / 1_048_576
    print(f"Wrote {len(features)} marine MPAs to {out_path} ({size_mb:.1f} MB)")
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch marine MPAs from WDPA (open ArcGIS service).")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--bbox", type=float, nargs=4,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Only fetch MPAs intersecting this box (recommended).",
    )
    group.add_argument(
        "--global", dest="world", action="store_true",
        help="Fetch every marine MPA on Earth (large download).",
    )
    parser.add_argument(
        "--out", type=Path, default=BACKEND_DATA / "mpas.geojson",
        help="Output GeoJSON path (default backend/data/mpas.geojson).",
    )
    parser.add_argument(
        "--simplify", action="store_true",
        help="Request lower-precision geometry to shrink the file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bbox = None if args.world else (args.bbox or [78.0, 5.5, 82.5, 10.0])
    scope = "GLOBAL" if args.world else f"bbox {bbox}"
    print(f"Fetching marine WDPA polygons ({scope})...")
    fetch_wdpa_marine(bbox, args.out, simplify=args.simplify)


if __name__ == "__main__":
    main()
