from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agents as agents_router
from app.api.routes import ais, events, geo, ingest, metrics, sar, verify
from app.core.config import settings
from app.services import gfw_ingest, mpa_index
from app.store.activity import activity_store
from app.store.repository import repo


def _run_ingest() -> None:
    """Blocking GFW ingest, run off the event loop in a worker thread.

    Building the global MPA index and pulling a worldwide SAR report each take
    several seconds, so this must NOT run in the startup path — otherwise the
    container misses the Cloud Run health check and crashes.
    """
    idx = mpa_index.get_index()  # lazy-loads the WDPA set here, in the thread
    print(f"MPA index: {idx.count} protected areas loaded from {idx.source}.")
    try:
        aggregates = gfw_ingest.fetch_activity()
    except Exception as exc:
        try:
            activity_store.failure(exc)
            category = activity_store.status()["error_category"]
        except Exception:
            category = "source_status_storage_unavailable"
        print(f"GFW activity fetch failed ({category}).")
        return
    try:
        activity_store.replace(aggregates)
        print(f"GFW activity: loaded {len(aggregates)} aggregate cells.")
    except Exception:
        print("GFW activity could not be stored.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo.load()  # sample events remain separate from GFW activity
    # Kick live ingestion off in the background so startup returns at once and
    # the server can answer the health check while the report loads.
    if settings.gfw_ingest_on_startup and gfw_ingest.ingestion_enabled():
        asyncio.create_task(asyncio.to_thread(_run_ingest))
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
app.include_router(sar.router)
app.include_router(verify.router)


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "events_loaded": len(repo.all()), "events_mode": repo.mode}
