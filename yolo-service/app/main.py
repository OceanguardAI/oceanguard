"""YOLO SAR inference service.

A small FastAPI app that, on demand, pulls a Sentinel-1 chip for a point and
runs the fine-tuned ship detector over it. Deployed as its own scale-to-zero
Cloud Run service so the heavy torch stack never burdens the main API.

Endpoints:
  GET  /health        -> liveness + whether the model and Sentinel Hub are ready
  POST /detect-point  -> {lat, lon, date?} -> YOLO detections + the analysed chip
"""
from __future__ import annotations

import base64
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app import inference, sentinel


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the model so the first officer click isn't slowed by torch load.
    inference.warm_up()
    yield


app = FastAPI(title="OceanGuard YOLO SAR Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class DetectPointRequest(BaseModel):
    lat: float
    lon: float
    date: str | None = None


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "sentinel_configured": sentinel.is_configured(),
        "model_path": str(settings.model_path),
        "model_exists": settings.model_path.exists(),
    }


@app.post("/detect-point")
def detect_point(req: DetectPointRequest) -> dict[str, object]:
    """Fetch a Sentinel-1 chip for the point and run YOLO over it."""
    if not sentinel.is_configured():
        raise HTTPException(status_code=503, detail="Sentinel Hub is not configured.")
    try:
        chip_png, bbox = sentinel.fetch_chip(req.lat, req.lon, req.date)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Sentinel Hub request failed: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch SAR chip: {exc}") from exc

    try:
        result = inference.detect(chip_png, bbox)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"YOLO inference failed: {exc}") from exc

    # Return the exact chip the model analysed (base64 PNG) so the UI can draw
    # the boxes over what YOLO actually saw.
    result["chip_bbox"] = bbox
    result["chip_png_b64"] = base64.b64encode(chip_png).decode("ascii")
    result["conf_threshold"] = settings.conf_threshold
    return result
