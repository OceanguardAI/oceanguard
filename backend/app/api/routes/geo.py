import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.core.config import settings

router = APIRouter()


@router.get("/mpa")
def get_mpa():
    """Return Bar Reef Marine Sanctuary GeoJSON for Leaflet polygon."""
    path = settings.data_dir / "bar_reef.geojson"
    return JSONResponse(content=json.loads(path.read_text()))


@router.get("/ports")
def get_ports():
    """Return nearby port/marina locations."""
    path = settings.data_dir / "ports.json"
    return json.loads(path.read_text())
