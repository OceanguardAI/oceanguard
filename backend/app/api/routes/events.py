from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.store.repository import repo
from app.models.schemas import RiskEvent, ReviewUpdate

router = APIRouter()


@router.get("/detections", response_model=list[RiskEvent])
def get_detections():
    """YOLO_SAR detections from xView3 validation scene (Proof A)."""
    return repo.all(source="YOLO_SAR")


@router.get("/risk-events", response_model=list[RiskEvent])
def get_risk_events(
    source: Optional[str] = Query(None, description="GFW or YOLO_SAR"),
    level:  Optional[str] = Query(None, description="LOW, MEDIUM, HIGH, CRITICAL"),
):
    """All risk events, optionally filtered by source and/or risk level."""
    return repo.all(source=source, level=level)


@router.get("/risk-events/{event_id}", response_model=RiskEvent)
def get_risk_event(event_id: str):
    event = repo.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")
    return event


@router.post("/risk-events/{event_id}/review", response_model=RiskEvent)
def update_review(event_id: str, body: ReviewUpdate):
    """Update the review_status of a single event (in-memory only)."""
    updated = repo.update_review(event_id, body.review_status)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")
    return updated
