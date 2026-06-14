from fastapi import APIRouter
from app.models.schemas import (
    RiskEvent, NarrateResponse, BriefingResponse,
    PatrolItem, AskRequest, AskResponse,
)
from app.agents import narrator, briefing as briefing_agent
from app.agents import patrol as patrol_agent, ask as ask_agent

router = APIRouter(prefix="/agents")


@router.post("/narrate", response_model=NarrateResponse)
async def narrate(event: RiskEvent):
    """Explain why a single vessel was flagged. Deterministic fallback always available."""
    return await narrator.narrate(event)


@router.post("/briefing", response_model=BriefingResponse)
async def daily_briefing(events: list[RiskEvent]):
    """Generate a daily situation summary for all provided events."""
    return await briefing_agent.briefing(events)


@router.post("/patrol", response_model=list[PatrolItem])
async def patrol(events: list[RiskEvent]):
    """Rank events by patrol priority. Deterministic fallback always available."""
    return await patrol_agent.patrol(events)


@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest):
    """Answer a natural language question using tool-augmented agentic loop."""
    return await ask_agent.ask(body.question)
