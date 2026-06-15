from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.agents import ask as ask_agent
from app.agents import briefing as briefing_agent
from app.agents import narrator, patrol as patrol_agent
from app.models.schemas import (
    AskRequest,
    AskResponse,
    BriefingResponse,
    NarrateResponse,
    PatrolItem,
    RiskEvent,
)
from app.store.repository import repo

router = APIRouter(prefix="/agents")


@router.post("/narrate", response_model=NarrateResponse)
async def narrate_event(event: RiskEvent) -> NarrateResponse:
    return await narrator.narrate(event)


@router.post("/narrate/{event_id}", response_model=NarrateResponse)
async def narrate_loaded_event(event_id: str) -> NarrateResponse:
    event = repo.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")
    return await narrator.narrate(event)


@router.post("/briefing", response_model=BriefingResponse)
async def daily_briefing(events: list[RiskEvent]) -> BriefingResponse:
    return await briefing_agent.briefing(events)


@router.post("/briefing/current", response_model=BriefingResponse)
async def current_briefing(
    source: str | None = Query(default=None, description="GFW or YOLO_SAR"),
    level: str | None = Query(default=None, description="LOW, MEDIUM, HIGH, CRITICAL"),
    review_status: str | None = Query(
        default=None,
        description="Pending, Confirmed Risk, False Positive, Resolved",
    ),
) -> BriefingResponse:
    events = repo.all(source=source, level=level, review_status=review_status)
    return await briefing_agent.briefing(events)


@router.post("/patrol", response_model=list[PatrolItem])
async def patrol(events: list[RiskEvent]) -> list[PatrolItem]:
    return await patrol_agent.patrol(events)


@router.post("/patrol/current", response_model=list[PatrolItem])
async def patrol_current(
    source: str | None = Query(default=None, description="GFW or YOLO_SAR"),
    level: str | None = Query(default=None, description="LOW, MEDIUM, HIGH, CRITICAL"),
    review_status: str | None = Query(
        default=None,
        description="Pending, Confirmed Risk, False Positive, Resolved",
    ),
) -> list[PatrolItem]:
    events = repo.all(source=source, level=level, review_status=review_status)
    return await patrol_agent.patrol(events)


@router.post("/ask", response_model=AskResponse)
async def ask_question(body: AskRequest) -> AskResponse:
    return await ask_agent.ask(body.question)
