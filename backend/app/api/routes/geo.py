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
def get_mpa() -> JSONResponse:
    """Serve the full marine protected area layer.

    Prefers the multi-MPA WDPA file (mpas.geojson); falls back to the single
    Bar Reef polygon so the map still renders when no WDPA data is present.
    """
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
