from __future__ import annotations

from typing import Literal

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
    mpa_name: str | None
    distance_to_mpa_km: float | None
    distance_from_port_km: float | None
    nearest_port: str | None
    timestamp: str
    review_status: str
    why_flagged: str
    uncertainty: str
    confidence_threshold: float
    recommended_action: str
    thumbnail: str | None


class ReviewUpdate(BaseModel):
    review_status: Literal["Pending", "Confirmed Risk", "False Positive", "Resolved"]


class ModelHistoryPoint(BaseModel):
    epoch: int
    map50: float
    loss: float


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
    training_history: list[ModelHistoryPoint]


class NarrateResponse(BaseModel):
    why_flagged: str
    uncertainty: str


class BriefingResponse(BaseModel):
    briefing: str


class PatrolItem(BaseModel):
    id: str
    rank: int
    risk_level: str
    distance_to_mpa_km: float | None
    justification: str


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


class RiskSummary(BaseModel):
    total_events: int
    source_counts: dict[str, int]
    risk_level_counts: dict[str, int]
    review_status_counts: dict[str, int]
    inside_mpa_count: int
    near_mpa_count: int
    highest_risk_event_id: str | None
    highest_risk_score: float | None
