"""Endpoints to pull live detection data and refresh the in-memory store."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.models.schemas import RiskEvent
from app.services import gfw_ingest
from app.store.repository import repo

router = APIRouter()


def _load_ports() -> list[dict]:
    path = settings.data_dir / "ports.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


@router.get("/ingest/status")
def ingest_status() -> dict[str, object]:
    return {
        "live_source": "Global Fishing Watch SAR",
        "gfw_token_configured": gfw_ingest.ingestion_enabled(),
        "region_bbox": settings.gfw_region_bbox,
        "lookback_days": settings.gfw_lookback_days,
        "events_loaded": len(repo.all()),
    }


@router.post("/ingest/gfw")
def ingest_gfw() -> dict[str, object]:
    if not gfw_ingest.ingestion_enabled():
        raise HTTPException(
            status_code=400,
            detail="GFW_API_TOKEN is not configured. Add it to backend/.env to enable live ingestion.",
        )
    try:
        events = gfw_ingest.fetch_live_events(ports=_load_ports())
    except Exception as exc:  # network / auth / parse failures
        raise HTTPException(status_code=502, detail=f"GFW ingestion failed: {exc}") from exc

    count = repo.replace_all(events)
    dark = sum(1 for e in events if not e.ais_matched)
    return {
        "ingested": count,
        "dark_vessels": dark,
        "ais_matched": count - dark,
        "source": "Global Fishing Watch SAR",
    }


@router.post("/ingest/push")
def ingest_push(events: list[RiskEvent], mode: str = "merge") -> dict[str, object]:
    """Receive externally-computed events (e.g. live YOLO/Sentinel-1 job).

    mode=merge upserts by id (keeps other sources); mode=replace swaps the store.
    """
    if mode not in {"merge", "replace"}:
        raise HTTPException(status_code=400, detail="mode must be 'merge' or 'replace'.")
    if mode == "replace":
        total = repo.replace_all(events)
    else:
        total = repo.upsert_many(events)
    return {"received": len(events), "total_events": total, "mode": mode}
