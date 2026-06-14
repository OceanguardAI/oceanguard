import json
from fastapi import APIRouter
from app.models.schemas import ModelMetrics
from app.core.config import settings

router = APIRouter()


@router.get("/model-metrics", response_model=ModelMetrics)
def get_model_metrics():
    """YOLO11n training and validation metrics."""
    path = settings.data_dir / "metrics.json"
    return ModelMetrics(**json.loads(path.read_text()))
