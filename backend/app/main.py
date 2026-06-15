from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agents as agents_router
from app.api.routes import events, geo, metrics
from app.store.repository import repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo.load()
    yield


app = FastAPI(
    title="OceanGuard AI",
    description="Dark vessel detection API for Marine Protected Areas",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(geo.router)
app.include_router(metrics.router)
app.include_router(agents_router.router)


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "events_loaded": len(repo.all())}
