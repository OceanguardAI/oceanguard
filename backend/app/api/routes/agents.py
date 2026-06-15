from __future__ import annotations

from fastapi import APIRouter

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

router = APIRouter(prefix="/agents")


@router.post("/narrate", response_model=NarrateResponse)
async def narrate_event(event: RiskEvent) -> NarrateResponse:
    return await narrator.narrate(event)


@router.post("/briefing", response_model=BriefingResponse)
async def daily_briefing(events: list[RiskEvent]) -> BriefingResponse:
    return await briefing_agent.briefing(events)


@router.post("/patrol", response_model=list[PatrolItem])
async def patrol(events: list[RiskEvent]) -> list[PatrolItem]:
    return await patrol_agent.patrol(events)


@router.post("/ask", response_model=AskResponse)
async def ask_question(body: AskRequest) -> AskResponse:
    return await ask_agent.ask(body.question)
