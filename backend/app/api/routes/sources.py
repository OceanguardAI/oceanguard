"""Unified read-only source readiness endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from app.services.source_health import get_source_health

router = APIRouter()


@router.get("/sources/status")
def source_status() -> dict[str, object]:
    return get_source_health()
