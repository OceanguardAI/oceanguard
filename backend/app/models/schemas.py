from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RiskEvent(BaseModel):
    id: str
    source: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
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


class ActivityAggregate(BaseModel):
    id: str
    dataset: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    detection_count: int = Field(ge=0)
    report_start: str
    report_end: str
    provider_time: str | None
    ingested_at: datetime


class ActivityPage(BaseModel):
    items: list[ActivityAggregate]
    total: int
    offset: int
    limit: int
    data_state: Literal["not_loaded", "available", "empty", "stale"]


class ReviewUpdate(BaseModel):
    review_status: Literal["Pending", "Confirmed Risk", "False Positive", "Resolved"]


class ReviewRecord(BaseModel):
    id: str
    event_id: str
    previous_status: str
    review_status: str
    reviewed_at: datetime
    actor_ref: str | None = None
    storage_scope: Literal["process_local", "database"]


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


class AgentStatus(BaseModel):
    provider: str
    provider_mode: str
    provider_enabled: bool
    provider_importable: bool
    client_ready: bool
    fallback_mode: bool
    model: str
    agent_max_tool_rounds: int
    agent_narrator_max_tokens: int
    agent_briefing_max_tokens: int
    agent_patrol_max_tokens: int
    agent_ask_max_tokens: int


class RiskSummary(BaseModel):
    total_events: int
    source_counts: dict[str, int]
    risk_level_counts: dict[str, int]
    review_status_counts: dict[str, int]
    inside_mpa_count: int
    near_mpa_count: int
    highest_risk_event_id: str | None
    highest_risk_score: float | None


class AcquisitionRecord(BaseModel):
    id: str
    source_id: str
    sensor: str
    external_id: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    footprint_geojson: dict | None = None
    resolution_m: float | None = Field(default=None, gt=0)
    evidence_uri: str | None = None


class ObservationRecord(BaseModel):
    id: str
    source_id: str
    acquisition_id: str | None = None
    observed_at: datetime
    ingested_at: datetime
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    uncertainty_m: float | None = Field(default=None, ge=0)
    model_version: str | None = None
    status: Literal["candidate", "accepted", "rejected"] = "candidate"
    evidence_id: str | None = None


class TrackRecord(BaseModel):
    id: str
    source_id: str
    state: Literal["tentative", "confirmed", "predicted", "lost", "ended"]
    first_observed_at: datetime
    last_observed_at: datetime
    identity_hypothesis: str | None = None
    identity_confidence: float | None = Field(default=None, ge=0, le=1)


class TrackPointRecord(BaseModel):
    track_id: str
    observed_at: datetime
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    is_predicted: bool = False
    uncertainty_m: float | None = Field(default=None, ge=0)
    observation_id: str | None = None


class AISMessageRecord(BaseModel):
    id: str
    mmsi: str
    message_at: datetime
    received_at: datetime
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    sog_knots: float | None = Field(default=None, ge=0)
    cog_degrees: float | None = Field(default=None, ge=0, le=360)
    heading_degrees: float | None = Field(default=None, ge=0, le=360)
    navigation_status: str | None = None
    quality: str | None = None


class AssociationRecord(BaseModel):
    id: str
    observation_id: str
    track_id: str | None = None
    ais_message_id: str | None = None
    score: float = Field(ge=0, le=1)
    decision: Literal["matched", "unmatched", "ambiguous", "unavailable"]
    method_version: str
    rejection_reasons: list[str] = Field(default_factory=list)


class EvidenceRecord(BaseModel):
    id: str
    kind: Literal["sar_image", "video_frame", "model_output", "ais_export", "report"]
    object_uri: str
    sha256: str
    acquisition_id: str | None = None
    model_version: str | None = None
    captured_at: datetime | None = None


class AlertRecord(BaseModel):
    id: str
    rule_version: str
    severity: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "acknowledged", "resolved", "dismissed"] = "open"
    starts_at: datetime
    ends_at: datetime | None = None
    uncertainty: str
    dedupe_key: str
    observation_ids: list[str] = Field(default_factory=list)
    association_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
