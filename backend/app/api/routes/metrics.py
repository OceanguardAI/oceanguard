from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.models.schemas import ModelMetrics

router = APIRouter()


@router.get("/model-metrics", response_model=ModelMetrics)
def get_model_metrics() -> ModelMetrics:
    path = settings.data_dir / "metrics.json"
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail="Required data file 'metrics.json' not found. Run the ML sync step.",
        )
    return ModelMetrics(**json.loads(path.read_text(encoding="utf-8")))
