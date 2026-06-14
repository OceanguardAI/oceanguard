from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel


class RiskEvent(BaseModel):
    id: str
    source: str
    lat: float
    lon: float
    risk_score: float
    risk_level: str
    sar_confidence: float
    image_quality: str
    ais_matched: bool
    ais_data_available: bool
    matching_method: str
    inside_mpa: bool
    near_mpa: bool
    mpa_name: Optional[str]
    distance_to_mpa_km: Optional[float]
    distance_from_port_km: Optional[float]
    nearest_port: Optional[str]
    timestamp: str
    review_status: str
    why_flagged: str
    uncertainty: str
    confidence_threshold: float
    recommended_action: str
    thumbnail: Optional[str]


class ReviewUpdate(BaseModel):
    review_status: Literal["Pending", "Confirmed Risk", "False Positive", "Resolved"]


class ModelMetrics(BaseModel):
    model: str
    dataset: str
    epochs: int
    map50: float
    map50_95: float
    precision: float
    recall: float
    confidence_threshold: float
    validation_scene: str
    detections_on_real_scene: int
    training_history: list[dict]


class NarrateResponse(BaseModel):
    why_flagged: str
    uncertainty: str


class BriefingResponse(BaseModel):
    briefing: str


class PatrolItem(BaseModel):
    id: str
    rank: int
    risk_level: str
    distance_to_mpa_km: Optional[float]
    justification: str


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
