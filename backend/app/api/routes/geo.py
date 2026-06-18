from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter()


def _load_required_json(filename: str) -> object:
    path = settings.data_dir / filename
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Required data file '{filename}' not found. Run the ML sync step.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/mpa")
def get_mpa(bbox: str | None = None) -> JSONResponse:
    """Serve the marine protected area layer.

    With ?bbox=min_lon,min_lat,max_lon,max_lat, returns only the MPAs that
    intersect that box (the map's viewport) so the global WDPA set never has to
    be sent or rendered all at once. Without a bbox, returns the full file
    (fine for the small Bar Reef fallback).
    """
    if bbox:
        try:
            min_lon, min_lat, max_lon, max_lat = (float(v) for v in bbox.split(","))
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="bbox must be 'min_lon,min_lat,max_lon,max_lat'.")
        from app.services import mpa_index

        fc = mpa_index.get_index().features_in_bbox(min_lon, min_lat, max_lon, max_lat)
        return JSONResponse(content=fc)

    filename = "mpas.geojson" if (settings.data_dir / "mpas.geojson").exists() else "bar_reef.geojson"
    return JSONResponse(content=_load_required_json(filename))


@router.get("/mpa/status")
def mpa_status() -> dict[str, object]:
    from app.services import mpa_index

    idx = mpa_index.get_index()
    return {
        "mpa_count": idx.count,
        "source_file": idx.source,
        "multi_mpa": idx.source == "mpas.geojson",
    }


@router.get("/ports")
def get_ports() -> list[dict]:
    payload = _load_required_json("ports.json")
    if not isinstance(payload, list):
        raise HTTPException(status_code=503, detail="ports.json is not a JSON list.")
    return payload
