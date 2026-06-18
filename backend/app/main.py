from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agents as agents_router
from app.api.routes import ais, events, geo, ingest, metrics
from app.core.config import settings
from app.services import gfw_ingest, mpa_index
from app.store.repository import repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo.load()
    # Load the marine protected area set (WDPA multi-MPA file or Bar Reef fallback).
    idx = mpa_index.get_index()
    print(f"MPA index: {idx.count} protected areas loaded from {idx.source}.")
    # Replace the seed dataset with live GFW SAR detections when configured.
    if settings.gfw_ingest_on_startup and gfw_ingest.ingestion_enabled():
        try:
            ports_path = settings.data_dir / "ports.json"
            ports = (
                json.loads(ports_path.read_text(encoding="utf-8"))
                if ports_path.exists()
                else []
            )
            events_live = gfw_ingest.fetch_live_events(ports=ports if isinstance(ports, list) else [])
            # In-memory only: keep the seed risk_events.json as an offline fallback.
            repo.replace_all(events_live, persist=False)
            print(f"Live ingestion: loaded {len(events_live)} GFW SAR events.")
        except Exception as exc:
            print(f"Live ingestion skipped (using seed data): {exc}")
    yield


app = FastAPI(
    title="OceanGuard AI",
    description="Dark vessel detection API for Marine Protected Areas",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(geo.router)
app.include_router(metrics.router)
app.include_router(agents_router.router)
app.include_router(ingest.router)
app.include_router(ais.router)


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "events_loaded": len(repo.all())}
