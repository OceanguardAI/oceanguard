# OceanGuard AI — Backend + Agents Team Plan (Team 2)

> **Team 2 — Backend + Agents.** Your job: build the FastAPI backend that serves `risk_events.json` and four Claude AI agents to the React frontend. You depend on Team 3 (ML Pipeline) to deliver `risk_events.json`. Do not change the RiskEvent schema. Do not add routes not listed here.

---

## What You Deliver

A running FastAPI backend at `http://localhost:8000` with:
- All `risk_events.json` CRUD routes
- MPA GeoJSON + model metrics endpoints
- 4 Claude AI agents (narrator, briefing, patrol, ask) — all with deterministic fallbacks

---

## Files You Own

```
backend/
├── requirements.txt
├── Dockerfile
├── data/
│   ├── risk_events.json     ← copy from ml/outputs/ (Team 3 delivers this)
│   ├── bar_reef.geojson     ← copy from ml/data/    (Team 3 delivers this)
│   ├── metrics.json         ← YOU WRITE THIS (hardcoded values)
│   └── ports.json           ← YOU WRITE THIS (hardcoded values)
├── tests/
│   ├── test_risk.py         ← implement
│   └── test_endpoints.py    ← implement
└── app/
    ├── main.py              ← implement (FastAPI app + lifespan)
    ├── core/
    │   └── config.py        ← implement (settings)
    ├── models/
    │   └── schemas.py       ← implement (Pydantic models)
    ├── store/
    │   └── repository.py    ← implement (in-memory event store)
    ├── agents/
    │   ├── __init__.py      ← empty
    │   ├── client.py        ← implement (Anthropic client singleton)
    │   ├── narrator.py      ← implement
    │   ├── briefing.py      ← implement
    │   ├── patrol.py        ← implement
    │   └── ask.py           ← implement (agentic loop)
    └── api/
        └── routes/
            ├── __init__.py  ← empty
            ├── events.py    ← implement
            ├── geo.py       ← implement
            ├── metrics.py   ← implement
            └── agents.py    ← implement
```

---

## Step 1 — Environment Setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt`:
```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
pydantic-settings>=2.2.0
pydantic>=2.7.0
anthropic>=0.28.0
shapely>=2.0.0
python-dotenv>=1.0.0
pytest>=7.0.0
httpx>=0.27.0
```

Create `.env` in `backend/`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Verify:
```bash
python -c "import fastapi, anthropic, shapely; print('all OK')"
```

---

## Step 2 — Data Files to Write

### `backend/data/metrics.json`

Write this file exactly as shown — these are the real model numbers:

```json
{
  "model": "YOLO11n",
  "dataset": "HRSID (2857 train / 715 val)",
  "epochs": 50,
  "map50": 0.838,
  "map50_95": 0.579,
  "precision": 0.830,
  "recall": 0.818,
  "confidence_threshold": 0.45,
  "validation_scene": "xView3 590dd08f71056cacv",
  "detections_on_real_scene": 122,
  "training_history": [
    {"epoch": 1,  "map50": 0.610, "loss": 1.80},
    {"epoch": 10, "map50": 0.720, "loss": 1.20},
    {"epoch": 20, "map50": 0.780, "loss": 0.90},
    {"epoch": 30, "map50": 0.810, "loss": 0.70},
    {"epoch": 40, "map50": 0.830, "loss": 0.60},
    {"epoch": 50, "map50": 0.838, "loss": 0.55}
  ]
}
```

### `backend/data/ports.json`

The OSM port from the Overpass query. Write this file:

```json
[
  {
    "name": "Marina",
    "type": "marina",
    "lat": 8.2155202,
    "lon": 79.7061466,
    "source": "OpenStreetMap Overpass"
  }
]
```

### Verify `backend/data/risk_events.json`

This file comes from Team 3 (ML Pipeline). Before writing any routes, confirm it has the right structure:

```bash
python -c "
import json
with open('data/risk_events.json') as f:
    events = json.load(f)
print(f'Total: {len(events)}')
gfw  = [e for e in events if e['source'] == 'GFW']
yolo = [e for e in events if e['source'] == 'YOLO_SAR']
print(f'GFW: {len(gfw)}, YOLO_SAR: {len(yolo)}')
b3 = next((e for e in events if e['id'] == 'bar-reef-003'), None)
if b3:
    print(f'bar-reef-003: score={b3[\"risk_score\"]}, level={b3[\"risk_level\"]}')
else:
    print('WARNING: bar-reef-003 not found')
"
```

Expected: `Total: 126, GFW: 4, YOLO_SAR: 122, bar-reef-003: score=0.61, level=HIGH`

---

## Step 3 — Pydantic Schemas

### `backend/app/models/schemas.py`

```python
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
```

---

## Step 4 — Settings

### `backend/app/core/config.py`

```python
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    data_dir: Path = Path(__file__).parent.parent.parent / "data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

---

## Step 5 — In-Memory Repository

### `backend/app/store/repository.py`

```python
"""In-memory store for risk events. Loaded once on startup."""
from __future__ import annotations
import json
from pathlib import Path
from app.models.schemas import RiskEvent
from app.core.config import settings


class RiskEventRepository:
    def __init__(self) -> None:
        self._events: dict[str, RiskEvent] = {}

    def load(self) -> None:
        """Load risk_events.json into memory."""
        path = settings.data_dir / "risk_events.json"
        if not path.exists():
            raise FileNotFoundError(
                f"risk_events.json not found at {path}. "
                "Run ml/build_risk_events.py first and copy to backend/data/."
            )
        raw: list[dict] = json.loads(path.read_text())
        self._events = {item["id"]: RiskEvent(**item) for item in raw}
        print(f"Loaded {len(self._events)} risk events from {path}")

    def all(
        self,
        source: str | None = None,
        level: str | None = None,
    ) -> list[RiskEvent]:
        events = list(self._events.values())
        if source:
            events = [e for e in events if e.source == source]
        if level:
            events = [e for e in events if e.risk_level == level]
        return events

    def get(self, event_id: str) -> RiskEvent | None:
        return self._events.get(event_id)

    def update_review(self, event_id: str, status: str) -> RiskEvent | None:
        event = self._events.get(event_id)
        if event is None:
            return None
        updated = event.model_copy(update={"review_status": status})
        self._events[event_id] = updated
        return updated


# Module-level singleton — imported by routes
repo = RiskEventRepository()
```

---

## Step 6 — FastAPI App + Routes

### `backend/app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.store.repository import repo
from app.api.routes import events, geo, metrics
from app.api.routes import agents as agents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load risk events on startup."""
    repo.load()
    yield


app = FastAPI(
    title="OceanGuard AI",
    description="Dark vessel detection API for Marine Protected Areas",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(geo.router)
app.include_router(metrics.router)
app.include_router(agents_router.router)


@app.get("/health")
def health():
    return {"status": "ok", "events_loaded": len(repo.all())}
```

### `backend/app/api/routes/events.py`

```python
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
```

### `backend/app/api/routes/geo.py`

```python
import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.core.config import settings

router = APIRouter()


@router.get("/mpa")
def get_mpa():
    """Return Bar Reef Marine Sanctuary GeoJSON for Leaflet polygon."""
    path = settings.data_dir / "bar_reef.geojson"
    return JSONResponse(content=json.loads(path.read_text()))


@router.get("/ports")
def get_ports():
    """Return nearby port/marina locations."""
    path = settings.data_dir / "ports.json"
    return json.loads(path.read_text())
```

### `backend/app/api/routes/metrics.py`

```python
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
```

---

## Step 7 — Anthropic Agent Client

### `backend/app/agents/client.py`

```python
"""Singleton Anthropic client. Returns None if API key is missing."""
from __future__ import annotations
import anthropic
from app.core.config import settings

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic | None:
    global _client
    if _client is not None:
        return _client
    if not settings.anthropic_api_key:
        return None
    _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client
```

---

## Step 8 — All 4 Agents

### Agent Design Principles

1. Every agent has a deterministic fallback — the system works without `ANTHROPIC_API_KEY`.
2. Agents never accuse, identify individuals, or claim certainty.
3. Responses are decision-support only — the officer decides.
4. Model: `claude-opus-4-8` for all agents.

---

### `backend/app/agents/narrator.py`

```python
"""Narrator agent: explain why a single vessel was flagged."""
from __future__ import annotations
from app.agents.client import get_client
from app.models.schemas import RiskEvent, NarrateResponse


SYSTEM_PROMPT = """You are a marine conservation analyst for OceanGuard AI.
Your role is to explain SAR vessel detections clearly for patrol officers.
Always use hedged language — say "may indicate", "suggests", "could be".
Never make accusations. Never identify individuals. Decisions are made by officers, not you.
Be factual, concise, and use 2-3 sentences per section."""


def _build_user_prompt(event: RiskEvent) -> str:
    lines = [
        f"Detection ID: {event.id}",
        f"Source: {event.source}",
        f"Location: {event.lat:.5f}N, {event.lon:.5f}E",
        f"Risk Score: {event.risk_score} ({event.risk_level})",
        f"SAR Confidence: {event.sar_confidence:.0%}",
        f"AIS Matched: {'Yes' if event.ais_matched else 'No'} "
        f"(AIS Data Available: {'Yes' if event.ais_data_available else 'No'})",
        f"Inside MPA: {'Yes' if event.inside_mpa else 'No'}",
        f"Near MPA (<=5km): {'Yes' if event.near_mpa else 'No'}",
        f"MPA Name: {event.mpa_name or 'N/A'}",
        f"Distance to MPA: {event.distance_to_mpa_km} km" if event.distance_to_mpa_km is not None else "Distance to MPA: N/A",
        f"Distance to Port: {event.distance_from_port_km} km" if event.distance_from_port_km is not None else "Distance to Port: N/A",
        f"Matching Method: {event.matching_method}",
        "",
        "In 2-3 sentences each:",
        "1. why_flagged: Why was this vessel flagged? Mention the key risk factors.",
        "2. uncertainty: What makes this uncertain? What could explain it innocently?",
        "",
        'Return as JSON: {"why_flagged": "...", "uncertainty": "..."}',
    ]
    return "\n".join(lines)


def _fallback(event: RiskEvent) -> NarrateResponse:
    dist_str = (
        f"{event.distance_to_mpa_km:.1f} km from {event.mpa_name}"
        if event.distance_to_mpa_km is not None and event.mpa_name
        else "in the monitored area"
    )
    ais_str = (
        "no matching AIS broadcast was found within the 2 km / 3-hour window"
        if event.ais_data_available
        else "AIS coverage was not available in this area"
    )

    why = (
        f"Vessel detected at {event.lat:.4f}N {event.lon:.4f}E at "
        f"{event.sar_confidence:.0%} SAR confidence. The detection is {dist_str} "
        f"and {ais_str}. Risk score: {event.risk_score:.2f} ({event.risk_level})."
    )
    uncertainty = (
        f"SAR-only detection ({event.sar_confidence:.0%} confidence) without confirmed AIS match. "
        "The vessel may be in transit, anchored legally, or using a different AIS identifier. "
        "A conservation officer should cross-reference with vessel tracking systems before any action."
    )
    return NarrateResponse(why_flagged=why, uncertainty=uncertainty)


async def narrate(event: RiskEvent) -> NarrateResponse:
    client = get_client()
    if client is None:
        return _fallback(event)

    try:
        import json as _json
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(event)}],
        )
        text = message.content[0].text.strip()
        if "{" in text:
            start = text.index("{")
            end   = text.rindex("}") + 1
            parsed = _json.loads(text[start:end])
            return NarrateResponse(
                why_flagged=parsed.get("why_flagged", ""),
                uncertainty=parsed.get("uncertainty", ""),
            )
        return NarrateResponse(why_flagged=text, uncertainty="")
    except Exception as e:
        print(f"Narrator agent error: {e}")
        return _fallback(event)
```

### `backend/app/agents/briefing.py`

```python
"""Briefing agent: daily situation summary for conservation officers."""
from __future__ import annotations
from app.agents.client import get_client
from app.models.schemas import RiskEvent, BriefingResponse


SYSTEM_PROMPT = """You are a senior marine conservation analyst.
Write a concise daily briefing for conservation officers.
Mention the highest-risk detection by name. Recommend an alertness level (LOW/ELEVATED/HIGH).
Use 3-5 sentences. Never make accusations. Decisions rest with human officers."""


def _build_user_prompt(events: list[RiskEvent]) -> str:
    lines = ["Summarise the following dark vessel detections for a daily briefing:", ""]
    for e in sorted(events, key=lambda x: x.risk_score, reverse=True):
        lines.append(
            f"- {e.id}: {e.risk_level} ({e.risk_score:.2f}), "
            f"{e.distance_to_mpa_km or 'N/A'} km from {e.mpa_name or 'MPA'}, "
            f"near_mpa={e.near_mpa}"
        )
    return "\n".join(lines)


def _fallback(events: list[RiskEvent]) -> BriefingResponse:
    if not events:
        return BriefingResponse(
            briefing="No dark vessel detections recorded. Continue routine monitoring."
        )
    top = max(events, key=lambda e: e.risk_score)
    high = [e for e in events if e.risk_level in ("HIGH", "CRITICAL")]
    briefing = (
        f"Monitoring update: {len(events)} SAR dark-vessel detections recorded near Bar Reef Marine Sanctuary. "
        f"Highest-risk detection is {top.id} (score {top.risk_score:.2f} / {top.risk_level}) "
        f"at {top.distance_to_mpa_km:.1f} km from {top.mpa_name}. "
        f"{len(high)} detection(s) rated HIGH or CRITICAL. "
        f"Alertness level: {'HIGH' if high else 'ELEVATED'}. "
        "All findings require human verification before any response."
    )
    return BriefingResponse(briefing=briefing)


async def briefing(events: list[RiskEvent]) -> BriefingResponse:
    client = get_client()
    if client is None or not events:
        return _fallback(events)

    try:
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(events)}],
        )
        return BriefingResponse(briefing=message.content[0].text.strip())
    except Exception as e:
        print(f"Briefing agent error: {e}")
        return _fallback(events)
```

### `backend/app/agents/patrol.py`

```python
"""Patrol agent: rank events for patrol priority."""
from __future__ import annotations
from app.agents.client import get_client
from app.models.schemas import RiskEvent, PatrolItem


SYSTEM_PROMPT = """You are a patrol planning assistant for marine conservation.
Rank the provided vessel detections from highest to lowest patrol priority.
Priority order: (1) inside MPA, (2) near MPA <=5km, (3) highest risk score.
Return a JSON array of objects: [{id, rank, risk_level, distance_to_mpa_km, justification}].
Justification: 1-2 sentences. Never make accusations. Officers decide."""


def _deterministic_rank(events: list[RiskEvent]) -> list[PatrolItem]:
    """Fallback: deterministic sort + template justifications."""
    def sort_key(e: RiskEvent):
        return (-int(e.inside_mpa), -int(e.near_mpa), -e.risk_score)

    sorted_events = sorted(events, key=sort_key)
    items = []
    for rank, event in enumerate(sorted_events, start=1):
        if event.inside_mpa:
            just = f"Vessel is inside {event.mpa_name} — highest priority for investigation."
        elif event.near_mpa:
            just = (
                f"Vessel is {event.distance_to_mpa_km:.1f} km from {event.mpa_name} "
                f"with no AIS match. Score {event.risk_score:.2f} ({event.risk_level})."
            )
        else:
            if event.distance_to_mpa_km is not None:
                just = (
                    f"Dark vessel detected {event.distance_to_mpa_km:.1f} km from monitored MPA. "
                    f"Risk score {event.risk_score:.2f} ({event.risk_level}). Routine verification recommended."
                )
            else:
                just = f"Dark vessel detected in monitored zone. Score {event.risk_score:.2f} ({event.risk_level})."

        items.append(PatrolItem(
            id=event.id,
            rank=rank,
            risk_level=event.risk_level,
            distance_to_mpa_km=event.distance_to_mpa_km,
            justification=just,
        ))
    return items


async def patrol(events: list[RiskEvent]) -> list[PatrolItem]:
    client = get_client()
    if client is None or not events:
        return _deterministic_rank(events)

    prompt = "Rank these detections for patrol priority:\n\n"
    for e in events:
        prompt += (
            f"- {e.id}: level={e.risk_level}, score={e.risk_score}, "
            f"inside_mpa={e.inside_mpa}, near_mpa={e.near_mpa}, "
            f"dist_km={e.distance_to_mpa_km}\n"
        )
    prompt += "\nReturn JSON array only."

    try:
        import json as _json
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        if "[" in text:
            start = text.index("[")
            end   = text.rindex("]") + 1
            parsed = _json.loads(text[start:end])
            return [PatrolItem(**item) for item in parsed]
        return _deterministic_rank(events)
    except Exception as e:
        print(f"Patrol agent error: {e}")
        return _deterministic_rank(events)
```

### `backend/app/agents/ask.py`

```python
"""Ask agent: agentic loop with tool use."""
from __future__ import annotations
import json
from app.agents.client import get_client
from app.models.schemas import AskResponse
from app.store.repository import repo


SYSTEM_PROMPT = """You are OceanGuard AI, a marine conservation decision-support assistant.
You help conservation officers understand vessel detection data.
You have tools to query detection data. Use them to give accurate, factual answers.
Never speculate beyond the data. Never make accusations. Never identify individuals.
Answer in 2-4 sentences. If uncertain, say so."""

TOOLS = [
    {
        "name": "query_detections",
        "description": "Query risk events. Use source='GFW' for dark vessel detections near Bar Reef, 'YOLO_SAR' for xView3 model validation detections.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Filter by source: 'GFW' or 'YOLO_SAR'",
                },
                "risk_level": {
                    "type": "string",
                    "description": "Filter by risk level: LOW, MEDIUM, HIGH, CRITICAL",
                },
            },
        },
    },
    {
        "name": "get_event",
        "description": "Get full details for a specific detection by ID (e.g. 'bar-reef-003').",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "The event ID, e.g. 'bar-reef-003'",
                }
            },
            "required": ["id"],
        },
    },
]


def _run_tool(name: str, inputs: dict) -> str:
    """Execute a tool call and return the result as a string."""
    if name == "query_detections":
        events = repo.all(
            source=inputs.get("source"),
            level=inputs.get("risk_level"),
        )
        if not events:
            return "No events found matching the filter."
        lines = [
            f"{e.id}: {e.risk_level} ({e.risk_score:.2f}), "
            f"{'near_mpa' if e.near_mpa else 'not near mpa'}, "
            f"dist={e.distance_to_mpa_km} km"
            for e in events[:10]
        ]
        return f"Found {len(events)} event(s):\n" + "\n".join(lines)

    elif name == "get_event":
        event = repo.get(inputs["id"])
        if event is None:
            return f"Event '{inputs['id']}' not found."
        return json.dumps(event.model_dump(), indent=2)

    return f"Unknown tool: {name}"


def _fallback(question: str) -> AskResponse:
    """Keyword-based fallback when no API key is available."""
    q = question.lower()

    if "bar-reef-003" in q or "highest" in q or "most" in q:
        return AskResponse(
            answer=(
                "bar-reef-003 is the highest-risk detection at 8.51N 79.68E. "
                "It is 0.4 km from Bar Reef Marine Sanctuary with a risk score of 0.61 (HIGH) "
                "and no matching AIS broadcast. A conservation officer should verify this detection."
            )
        )
    if "dark vessel" in q or "what is" in q or "what does" in q:
        return AskResponse(
            answer=(
                "A dark vessel is a ship that has disabled or is not broadcasting its AIS transponder. "
                "SAR satellites detect all vessels regardless of AIS status. "
                "OceanGuard cross-references SAR detections with AIS data — unmatched detections are flagged for review."
            )
        )
    if "mpa" in q or "bar reef" in q:
        return AskResponse(
            answer=(
                "Bar Reef Marine Sanctuary is a protected marine area off the northwest coast of Sri Lanka (WDPA ID 4783). "
                "Any vessel detected within 5 km is flagged as near-MPA. "
                "bar-reef-003 is 0.4 km from its boundary — the closest detection in this dataset."
            )
        )
    if "how many" in q or "total" in q or "count" in q:
        gfw  = repo.all(source="GFW")
        high = [e for e in gfw if e.risk_level in ("HIGH", "CRITICAL")]
        return AskResponse(
            answer=(
                f"There are {len(gfw)} GFW dark-vessel detections near Bar Reef Marine Sanctuary. "
                f"{len(high)} are rated HIGH or CRITICAL risk. "
                "bar-reef-003 is the only one within 1 km of the MPA boundary."
            )
        )

    return AskResponse(
        answer=(
            "I can help with questions about the dark vessel detections near Bar Reef Marine Sanctuary. "
            "Try asking about specific detections (e.g. bar-reef-003), risk levels, or distances to the MPA."
        )
    )


async def ask(question: str) -> AskResponse:
    client = get_client()
    if client is None:
        return _fallback(question)

    messages = [{"role": "user", "content": question}]

    try:
        # Agentic loop: Claude calls tools until it produces a final text answer
        for _ in range(5):  # max 5 tool rounds
            response = client.messages.create(
                model="claude-opus-4-8",
                max_tokens=800,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return AskResponse(answer=block.text.strip())
                break

            if response.stop_reason == "tool_use":
                assistant_content = response.content
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        result_text = _run_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                        })
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        return _fallback(question)

    except Exception as e:
        print(f"Ask agent error: {e}")
        return _fallback(question)
```

### `backend/app/api/routes/agents.py`

```python
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
```

---

## Step 9 — Tests

### `backend/tests/test_risk.py`

```python
"""Tests for the risk scoring formula. Imports from ml pipeline."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ml"))

from pipeline.risk import calculate_risk


def test_bar_reef_003_exact():
    """Canonical case — must yield exactly 0.61 / HIGH."""
    score, level = calculate_risk(
        detection_conf=0.70,
        ais_matched=False,
        ais_data_available=True,
        inside_mpa=False,
        near_mpa=True,
        image_quality_score=1.0,
    )
    assert score == 0.61, f"Expected 0.61, got {score}"
    assert level == "HIGH", f"Expected HIGH, got {level}"


def test_inside_mpa_raises_score():
    score, level = calculate_risk(
        detection_conf=0.70, ais_matched=False, ais_data_available=True,
        inside_mpa=True, near_mpa=False, image_quality_score=1.0,
    )
    assert score > 0.61
    assert level in ("HIGH", "CRITICAL")


def test_ais_matched_reduces_score():
    score_un, _ = calculate_risk(0.70, False, True, False, False, 1.0)
    score_ma, _ = calculate_risk(0.70, True,  True, False, False, 1.0)
    assert score_ma < score_un


def test_no_ais_data_neutral():
    score, level = calculate_risk(0.70, False, False, False, False, 1.0)
    # ais_score=0.3 (neutral), mpa_score=0 -> risk = 0.21 + 0.075 = 0.285
    assert score == 0.285
    assert level == "LOW"


def test_degraded_image_reduces_score():
    full, _ = calculate_risk(0.70, False, True, False, True, 1.0)
    half, _ = calculate_risk(0.70, False, True, False, True, 0.5)
    assert half < full


def test_critical_threshold():
    _, level = calculate_risk(1.0, False, True, True, False, 1.0,
                              fishing_score=1.0, repeated_activity_score=1.0)
    assert level == "CRITICAL"


def test_low_threshold():
    _, level = calculate_risk(0.10, True, True, False, False, 1.0)
    assert level == "LOW"
```

### `backend/tests/test_endpoints.py`

```python
"""Integration tests for FastAPI routes using in-memory fixtures."""
import json, os, pytest
from pathlib import Path
from fastapi.testclient import TestClient


FIXTURE_EVENT = {
    "id": "bar-reef-003",
    "source": "GFW",
    "lat": 8.51, "lon": 79.68,
    "risk_score": 0.61, "risk_level": "HIGH",
    "sar_confidence": 0.70, "image_quality": "Good",
    "ais_matched": False, "ais_data_available": True,
    "matching_method": "Spatial 2km + 3hr time window",
    "inside_mpa": False, "near_mpa": True,
    "mpa_name": "Bar Reef Marine Sanctuary",
    "distance_to_mpa_km": 0.4, "distance_from_port_km": 33.1,
    "nearest_port": "Marina (OSM)",
    "timestamp": "2026-06-09T14:32:00Z",
    "review_status": "Pending",
    "why_flagged": "", "uncertainty": "",
    "confidence_threshold": 0.45,
    "recommended_action": "Human reviewer should verify scene.",
    "thumbnail": None,
}

FIXTURE_METRICS = {
    "model": "YOLO11n", "dataset": "HRSID", "epochs": 50,
    "map50": 0.838, "map50_95": 0.579, "precision": 0.830, "recall": 0.818,
    "confidence_threshold": 0.45, "validation_scene": "xView3",
    "detections_on_real_scene": 122, "training_history": [],
}

FIXTURE_GEOJSON = {
    "type": "Feature",
    "geometry": {"type": "Polygon", "coordinates": [[[79.7, 8.3], [79.8, 8.5], [79.6, 8.5], [79.7, 8.3]]]},
    "properties": {"NAME": "Bar Reef"},
}


@pytest.fixture
def client(tmp_path):
    (tmp_path / "risk_events.json").write_text(json.dumps([FIXTURE_EVENT]))
    (tmp_path / "metrics.json").write_text(json.dumps(FIXTURE_METRICS))
    (tmp_path / "bar_reef.geojson").write_text(json.dumps(FIXTURE_GEOJSON))
    (tmp_path / "ports.json").write_text(json.dumps([{"name": "Marina", "lat": 8.21, "lon": 79.70}]))

    # Patch settings and reload store
    from unittest.mock import patch
    with patch("app.core.config.settings") as mock_cfg:
        mock_cfg.data_dir = tmp_path
        mock_cfg.anthropic_api_key = ""
        # Re-import app after patching
        from app.store.repository import repo
        repo._events = {}
        repo.load()
        from app.main import app
        yield TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_list_risk_events(client):
    r = client.get("/risk-events")
    assert r.status_code == 200
    assert r.json()[0]["id"] == "bar-reef-003"


def test_get_single_event(client):
    r = client.get("/risk-events/bar-reef-003")
    assert r.status_code == 200
    assert r.json()["risk_score"] == 0.61


def test_event_not_found(client):
    assert client.get("/risk-events/no-such").status_code == 404


def test_filter_source(client):
    r = client.get("/risk-events?source=GFW")
    assert all(e["source"] == "GFW" for e in r.json())


def test_filter_level(client):
    r = client.get("/risk-events?level=HIGH")
    assert all(e["risk_level"] == "HIGH" for e in r.json())


def test_update_review(client):
    r = client.post("/risk-events/bar-reef-003/review", json={"review_status": "Confirmed Risk"})
    assert r.status_code == 200
    assert r.json()["review_status"] == "Confirmed Risk"


def test_update_review_not_found(client):
    assert client.post("/risk-events/nope/review", json={"review_status": "Pending"}).status_code == 404


def test_metrics(client):
    r = client.get("/model-metrics")
    assert r.status_code == 200
    assert r.json()["map50"] == 0.838


def test_mpa(client):
    r = client.get("/mpa")
    assert r.status_code == 200
    assert r.json()["type"] == "Feature"


def test_narrate_fallback(client):
    r = client.post("/agents/narrate", json=FIXTURE_EVENT)
    assert r.status_code == 200
    body = r.json()
    assert len(body.get("why_flagged", "")) > 10
    assert "uncertainty" in body


def test_briefing_fallback(client):
    r = client.post("/agents/briefing", json=[FIXTURE_EVENT])
    assert r.status_code == 200
    assert len(r.json().get("briefing", "")) > 10


def test_patrol_fallback(client):
    r = client.post("/agents/patrol", json=[FIXTURE_EVENT])
    assert r.status_code == 200
    items = r.json()
    assert items[0]["rank"] == 1
    assert items[0]["id"] == "bar-reef-003"


def test_ask_fallback(client):
    r = client.post("/agents/ask", json={"question": "Which detection is highest risk?"})
    assert r.status_code == 200
    assert "bar-reef-003" in r.json()["answer"]
```

---

## Step 10 — Run Tests

```bash
cd backend
pytest tests/ -v
```

All tests should pass even without `ANTHROPIC_API_KEY` — deterministic fallbacks handle agent routes.

---

## Step 11 — Run the Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify all routes:
```bash
curl http://localhost:8000/health
# {"status":"ok","events_loaded":126}

curl http://localhost:8000/risk-events/bar-reef-003
# {"id":"bar-reef-003","risk_score":0.61,"risk_level":"HIGH",...}

curl "http://localhost:8000/risk-events?source=GFW"
# Array of 4 GFW events

curl http://localhost:8000/model-metrics
# {"model":"YOLO11n","map50":0.838,...}

curl -X POST http://localhost:8000/agents/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Which detection is highest risk?"}'
# {"answer":"bar-reef-003 is the highest-risk..."}
```

---

## Step 12 — Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## `__init__.py` Files Required

Create these as empty files (Python needs them for imports):

```
backend/app/__init__.py
backend/app/core/__init__.py
backend/app/models/__init__.py
backend/app/store/__init__.py
backend/app/agents/__init__.py
backend/app/api/__init__.py
backend/app/api/routes/__init__.py
```

Command to create all at once:
```bash
mkdir -p app/core app/models app/store app/agents app/api/routes tests
touch app/__init__.py app/core/__init__.py app/models/__init__.py \
      app/store/__init__.py app/agents/__init__.py \
      app/api/__init__.py app/api/routes/__init__.py
```

---

## Verification Checklist

- [ ] `pytest tests/ -v` — all tests pass
- [ ] `GET /health` → `{"status": "ok", "events_loaded": 126}`
- [ ] `GET /risk-events/bar-reef-003` → `risk_score=0.61, risk_level="HIGH"`
- [ ] `GET /risk-events?source=GFW` → exactly 4 events
- [ ] `GET /risk-events?source=YOLO_SAR` → 122 events
- [ ] `GET /model-metrics` → `map50=0.838`
- [ ] `GET /mpa` → valid GeoJSON Feature with Bar Reef polygon
- [ ] `POST /agents/narrate` works without API key
- [ ] `POST /agents/patrol` returns `bar-reef-003` as rank 1
- [ ] `POST /agents/ask` with "Which detection is highest risk?" mentions `bar-reef-003`
- [ ] CORS headers on all responses: `curl -I -H "Origin: http://localhost:5173" http://localhost:8000/health`
- [ ] `docker build -t oceanguard-backend .` succeeds

---

## Common Problems

| Problem | Cause | Fix |
|---|---|---|
| `FileNotFoundError: risk_events.json` | Not copied from ML team | `cp ml/outputs/risk_events.json backend/data/` |
| `ImportError: No module named 'app'` | Wrong working directory | Always run from `backend/` |
| `422 Unprocessable Entity` on narrate | Body doesn't match RiskEvent schema | All 24 fields must be present; `thumbnail` can be `null` |
| CORS error in browser | Origin not in allow_origins | Add `http://localhost:5173` to CORSMiddleware |
| Agent silently fails | Exception swallowed | Check stderr for "agent error:" prints |
| `anthropic_api_key` empty | `.env` not found | Place `.env` in `backend/` directory |
| Tool loop never ends | Claude doesn't return `end_turn` | The `for _ in range(5)` cap prevents infinite loops |
| Pydantic validation error | `review_status` has wrong value | Only these exact values are valid: Pending, Confirmed Risk, False Positive, Resolved |

---

## What You Do NOT Own

- Do NOT touch `ml/` files
- Do NOT touch `frontend/` files
- Do NOT change the `RiskEvent` schema field names — frontend depends on exact names
- Do NOT change the risk formula (`pipeline/risk.py`)
- Do NOT add API routes not in this plan
- Do NOT call GFW or xView3 APIs at runtime — all data is static JSON from `backend/data/`
