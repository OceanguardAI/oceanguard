from __future__ import annotations

import json

from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import ModelMetrics

router = APIRouter()


@router.get("/model-metrics", response_model=ModelMetrics)
def get_model_metrics() -> ModelMetrics:
    path = settings.data_dir / "metrics.json"
    return ModelMetrics(**json.loads(path.read_text(encoding="utf-8")))
