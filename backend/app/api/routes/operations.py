"""Versioned read APIs for durable operational records."""
from __future__ import annotations

import math
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.models.schemas import AlertRecord, ObservationRecord, TrackPointRecord, TrackRecord
from app.store.operational import PostgresOperationalStore

router = APIRouter(prefix="/v1")


def _store() -> PostgresOperationalStore:
    if not settings.database_url:
        raise HTTPException(status_code=503, detail="Operational database is not configured.")
    return PostgresOperationalStore(settings.database_url)


def _bbox(value: str | None) -> tuple[float, float, float, float] | None:
    if value is None:
        return None
    try:
        values = tuple(float(part) for part in value.split(","))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="bbox must be west,south,east,north") from exc
    if (
        len(values) != 4 or not all(math.isfinite(v) for v in values)
        or not (-180 <= values[0] < values[2] <= 180)
        or not (-90 <= values[1] < values[3] <= 90)
    ):
        raise HTTPException(status_code=422, detail="bbox must be west,south,east,north")
    return values


@router.get("/observations", response_model=list[ObservationRecord])
def get_observations(
    start: datetime | None = None,
    end: datetime | None = None,
    bbox: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[ObservationRecord]:
    return _store().observations(start=start, end=end, bbox=_bbox(bbox), limit=limit, offset=offset)


@router.get("/tracks", response_model=list[TrackRecord])
def get_tracks(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[TrackRecord]:
    return _store().tracks(limit=limit, offset=offset)


@router.get("/tracks/{track_id}/points", response_model=list[TrackPointRecord])
def get_track_points(
    track_id: str,
    limit: int = Query(default=1000, ge=1, le=5000),
) -> list[TrackPointRecord]:
    return _store().track_points(track_id, limit=limit)


@router.get("/alerts", response_model=list[AlertRecord])
def get_alerts(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[AlertRecord]:
    return _store().alerts(status=status, limit=limit)
