"""Run the fine-tuned YOLO ship detector (best.pt) on a SAR chip.

The model is loaded once at process start (lazy singleton) and reused. Detection
pixel coordinates are converted to latitude/longitude by linear interpolation
across the chip's geographic bbox — accurate for a small EPSG:4326 chip.
"""
from __future__ import annotations

import io
import threading
from typing import Any

import numpy as np
from PIL import Image

from app.config import settings

_model: Any = None
_model_lock = threading.Lock()


def _get_model() -> Any:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from ultralytics import YOLO  # imported lazily: heavy

                _model = YOLO(str(settings.model_path))
    return _model


def warm_up() -> bool:
    """Load the model so the first real request isn't slowed by import+load."""
    try:
        _get_model()
        return True
    except Exception:
        return False


def _px_to_lonlat(px: float, py: float, bbox: list[float], size: int) -> tuple[float, float]:
    """Map a pixel (px, py) in a size×size chip to (lon, lat) via its bbox.

    Image rows increase downward, so latitude decreases as py increases.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    lon = min_lon + (px / size) * (max_lon - min_lon)
    lat = max_lat - (py / size) * (max_lat - min_lat)
    return lon, lat


def detect(chip_png: bytes, bbox: list[float]) -> dict[str, Any]:
    """Run YOLO on a SAR chip; return detections with pixel + geo coordinates.

    Returns a dict with: found, count, best_confidence, detections[] (each with
    confidence, bbox_px [x1,y1,x2,y2], lat, lon), and the chip size in pixels.
    """
    image = Image.open(io.BytesIO(chip_png)).convert("RGB")
    arr = np.array(image)
    size = settings.chip_px

    model = _get_model()
    results = model.predict(source=arr, conf=settings.conf_threshold, verbose=False, device="cpu")

    detections: list[dict[str, Any]] = []
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            x1, y1, x2, y2 = (round(v, 1) for v in box.xyxy[0].tolist())
            conf = round(float(box.conf[0]), 4)
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            lon, lat = _px_to_lonlat(cx, cy, bbox, size)
            detections.append(
                {
                    "confidence": conf,
                    "bbox_px": [x1, y1, x2, y2],
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                }
            )

    detections.sort(key=lambda d: d["confidence"], reverse=True)
    return {
        "found": len(detections) > 0,
        "count": len(detections),
        "best_confidence": detections[0]["confidence"] if detections else 0.0,
        "detections": detections,
        "chip_px": size,
    }
