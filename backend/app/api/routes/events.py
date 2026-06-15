from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ReviewUpdate, RiskEvent, RiskSummary
from app.store.repository import repo

router = APIRouter()


@router.get("/detections", response_model=list[RiskEvent])
def get_detections() -> list[RiskEvent]:
    return repo.all(source="YOLO_SAR")


@router.get("/risk-events", response_model=list[RiskEvent])
def get_risk_events(
    source: str | None = Query(default=None, description="GFW or YOLO_SAR"),
    level: str | None = Query(default=None, description="LOW, MEDIUM, HIGH, CRITICAL"),
    review_status: str | None = Query(
        default=None,
        description="Pending, Confirmed Risk, False Positive, Resolved",
    ),
) -> list[RiskEvent]:
    return repo.all(source=source, level=level, review_status=review_status)


@router.get("/risk-summary", response_model=RiskSummary)
def get_risk_summary() -> RiskSummary:
    return repo.summary()


@router.get("/risk-events/{event_id}", response_model=RiskEvent)
def get_risk_event(event_id: str) -> RiskEvent:
    event = repo.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")
    return event


@router.post("/risk-events/{event_id}/review", response_model=RiskEvent)
def update_review(event_id: str, body: ReviewUpdate) -> RiskEvent:
    updated = repo.update_review(event_id, body.review_status)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")
    return updated
