from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.agents import ask as ask_agent
from app.agents import briefing as briefing_agent
from app.agents.client import (
    gemini_provider_enabled,
    gemini_provider_mode,
    genai_importable,
    get_client,
)
from app.agents import narrator, patrol as patrol_agent
from app.core.config import settings
from app.models.schemas import (
    AgentStatus,
    AskRequest,
    AskResponse,
    BriefingResponse,
    NarrateResponse,
    PatrolItem,
    RiskEvent,
)
from app.store.repository import repo

router = APIRouter(prefix="/agents")


@router.get("/status", response_model=AgentStatus)
async def agent_status() -> AgentStatus:
    client = get_client()
    return AgentStatus(
        provider="gemini",
        provider_mode=gemini_provider_mode(),
        provider_enabled=gemini_provider_enabled(),
        provider_importable=genai_importable(),
        client_ready=client is not None,
        fallback_mode=client is None,
        model=settings.gemini_model,
        agent_max_tool_rounds=settings.agent_max_tool_rounds,
        agent_narrator_max_tokens=settings.agent_narrator_max_tokens,
        agent_briefing_max_tokens=settings.agent_briefing_max_tokens,
        agent_patrol_max_tokens=settings.agent_patrol_max_tokens,
        agent_ask_max_tokens=settings.agent_ask_max_tokens,
    )


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
