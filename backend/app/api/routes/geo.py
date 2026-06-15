from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter()


@router.get("/mpa")
def get_mpa() -> JSONResponse:
    path = settings.data_dir / "bar_reef.geojson"
    return JSONResponse(content=json.loads(path.read_text(encoding="utf-8")))


@router.get("/ports")
def get_ports() -> list[dict]:
    path = settings.data_dir / "ports.json"
    return json.loads(path.read_text(encoding="utf-8"))
