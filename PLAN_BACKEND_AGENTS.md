# OceanGuard AI — Backend & Agents Team Plan

> **Team 2 — Backend + Agents.** Your job: build the FastAPI service that serves risk events and hosts the 4 Claude AI agents. The frontend calls your API; the ML team feeds you `risk_events.json`.

---

## Your Deliverable

A running FastAPI server at `http://localhost:8000` with all routes working and all 4 agents responding (with deterministic fallbacks if no API key is present).

---

## Files You Own

```
backend/
├── requirements.txt              ← already written
├── Dockerfile                    ← implement
├── data/
│   ├── risk_events.json          ← copied from ml/outputs/ by ML team
│   ├── bar_reef.geojson          ← copied from ml/data/ by ML team
│   ├── ports.json                ← write this (converted from overpass JSON)
│   └── metrics.json              ← write this (hardcoded real model metrics)
├── tests/
│   ├── test_risk.py              ← implement
│   └── test_endpoints.py         ← implement
└── app/
    ├── __init__.py
    ├── main.py                   ← implement
    ├── core/
    │   ├── __init__.py
    │   └── config.py             ← implement
    ├── models/
    │   ├── __init__.py
    │   └── schemas.py            ← implement
    ├── store/
    │   ├── __init__.py
    │   └── repository.py         ← implement
    ├── services/
    │   ├── __init__.py
    │   └── risk_service.py       ← implement
    ├── agents/
    │   ├── __init__.py
    │   ├── client.py             ← implement
    │   ├── narrator.py           ← implement
    │   ├── briefing.py           ← implement
    │   ├── patrol.py             ← implement
    │   └── ask.py                ← implement
    └── api/
        ├── __init__.py
        └── routes/
            ├── __init__.py
            ├── detections.py     ← implement
            ├── risk_events.py    ← implement
            ├── geo.py            ← implement
            ├── metrics.py        ← implement
            └── agents.py         ← implement
```

---

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` (already written):
```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic-settings>=2.0.0
anthropic>=0.25.0
shapely>=2.0.0
python-dotenv>=1.0.0
pytest>=7.0.0
httpx>=0.27.0
```

---

## Environment Variables

Create `.env` in the project root (never commit):
```
ANTHROPIC_API_KEY=sk-ant-...
```

Read in `app/core/config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    data_dir: str = "data"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Data Files to Write

### `backend/data/metrics.json`

Hardcoded real model metrics — write this file manually:

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
    {"epoch": 1,  "map50": 0.61,  "loss": 1.80},
    {"epoch": 10, "map50": 0.72,  "loss": 1.20},
    {"epoch": 20, "map50": 0.78,  "loss": 0.90},
    {"epoch": 30, "map50": 0.81,  "loss": 0.70},
    {"epoch": 40, "map50": 0.83,  "loss": 0.60},
    {"epoch": 50, "map50": 0.838, "loss": 0.55}
  ]
}
```

### `backend/data/ports.json`

The OSM port near Bar Reef:
```json
[
  {
    "name": "Marina (OSM)",
    "lat": 8.2155202,
    "lon": 79.7061466
  }
]
```

---

## `app/models/schemas.py`

```python
from typing import Optional, Literal
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
    mpa_name: Optional[str] = None
    distance_to_mpa_km: Optional[float] = None
    distance_from_port_km: Optional[float] = None
    nearest_port: Optional[str] = None
    timestamp: str
    review_status: str = "Pending"
    why_flagged: str = ""
    uncertainty: str = ""
    confidence_threshold: float = 0.45
    recommended_action: str = "Human reviewer should verify scene and external context."
    thumbnail: Optional[str] = None

class ReviewUpdate(BaseModel):
    review_status: Literal["Pending", "Confirmed Risk", "False Positive", "Resolved"]

class NarratorResponse(BaseModel):
    why_flagged: str
    uncertainty: str

class PatrolItem(BaseModel):
    id: str
    rank: int
    risk_level: str
    distance_to_mpa_km: Optional[float]
    justification: str

class AskRequest(BaseModel):
    question: str
```

---

## `app/store/repository.py`

In-memory store loaded from JSON at startup:

```python
import json
from pathlib import Path
from app.models.schemas import RiskEvent

_events: list[RiskEvent] = []

def load(data_dir: str = "data"):
    global _events
    path = Path(data_dir) / "risk_events.json"
    with open(path) as f:
        _events = [RiskEvent(**e) for e in json.load(f)]

def list_events(source: str | None = None, risk_level: str | None = None) -> list[RiskEvent]:
    result = _events
    if source:
        result = [e for e in result if e.source == source]
    if risk_level:
        result = [e for e in result if e.risk_level == risk_level]
    return result

def get_event(event_id: str) -> RiskEvent | None:
    return next((e for e in _events if e.id == event_id), None)

def update_review(event_id: str, status: str) -> bool:
    for e in _events:
        if e.id == event_id:
            e.review_status = status
            return True
    return False
```

---

## `app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.store import repository
from app.api.routes import detections, risk_events, geo, metrics, agents

app = FastAPI(title="OceanGuard AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    repository.load()

app.include_router(detections.router)
app.include_router(risk_events.router)
app.include_router(geo.router)
app.include_router(metrics.router)
app.include_router(agents.router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

---

## API Routes

### `api/routes/risk_events.py`
```python
from fastapi import APIRouter, HTTPException, Query
from app.store import repository
from app.models.schemas import RiskEvent, ReviewUpdate

router = APIRouter(prefix="/risk-events", tags=["risk-events"])

@router.get("", response_model=list[RiskEvent])
def list_risk_events(source: str | None = Query(None), level: str | None = Query(None)):
    return repository.list_events(source=source, risk_level=level)

@router.get("/{event_id}", response_model=RiskEvent)
def get_risk_event(event_id: str):
    event = repository.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.post("/{event_id}/review")
def update_review(event_id: str, body: ReviewUpdate):
    if not repository.update_review(event_id, body.review_status):
        raise HTTPException(status_code=404, detail="Event not found")
    return {"id": event_id, "review_status": body.review_status}
```

### `api/routes/detections.py`
```python
# GET /detections → YOLO_SAR events only
```

### `api/routes/geo.py`
```python
# GET /mpa → serve backend/data/bar_reef.geojson
# GET /ports → serve backend/data/ports.json
```

### `api/routes/metrics.py`
```python
# GET /model-metrics → serve backend/data/metrics.json
```

### `api/routes/agents.py`
```python
# POST /agents/narrate  → narrator.narrate(event)
# POST /agents/briefing → briefing.brief(events)
# POST /agents/patrol   → patrol.rank(events)
# POST /agents/ask      → ask.answer(question)
```

---

## Agents

All agents use `claude-opus-4-8`. All have deterministic fallbacks — the demo must work without an API key.

### `agents/client.py`

```python
import anthropic
from app.core.config import settings

_client: anthropic.Anthropic | None = None

def get_client() -> anthropic.Anthropic | None:
    global _client
    if not settings.anthropic_api_key:
        return None
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client
```

---

### `agents/narrator.py` — `POST /agents/narrate`

**Input:** single RiskEvent  
**Output:** `{"why_flagged": "...", "uncertainty": "..."}`

**System prompt:**
```
You are a marine conservation analyst providing decision-support to patrol officers.
Explain detections clearly and factually. Never make accusations or assign guilt.
Always note what is uncertain. The officer makes all final decisions.
```

**User prompt:**
```
A vessel was detected at {lat:.4f}°N, {lon:.4f}°E.
SAR confidence: {sar_confidence:.0%}.
AIS status: {"no matching broadcast found" if not ais_matched else "AIS match found"} within 2 km / 3 hours ({matching_method}).
Distance to {mpa_name}: {distance_to_mpa_km:.1f} km ({"NEAR MPA" if near_mpa else "outside MPA zone"}).
Risk score: {risk_score} ({risk_level}).

In 2-3 sentences explain why this was flagged and what makes it uncertain.
Return JSON only: {"why_flagged": "...", "uncertainty": "..."}
```

**Fallback (no API key):**
```python
def _fallback(event) -> dict:
    mpa_dist = f"{event.distance_to_mpa_km:.1f} km" if event.distance_to_mpa_km else "unknown distance"
    return {
        "why_flagged": (
            f"Vessel detected at {event.lat:.3f}°N, {event.lon:.3f}°E shows no matching AIS "
            f"broadcast within 2 km / 3 hours, placing it {mpa_dist} from "
            f"{event.mpa_name or 'the monitored MPA'}. "
            f"Risk score {event.risk_score:.2f} ({event.risk_level}) driven by unmatched AIS "
            f"and MPA proximity."
        ),
        "uncertainty": (
            f"SAR detection confidence is {event.sar_confidence:.0%}. "
            "AIS absence may reflect equipment failure rather than intentional evasion. "
            "A conservation officer should verify against additional imagery and context."
        ),
    }
```

---

### `agents/briefing.py` — `POST /agents/briefing`

**Input:** list of RiskEvents (send all GFW events)  
**Output:** `{"briefing": "..."}`

**System prompt:** Same as narrator.

**User prompt:** Include count of events, highest-risk event details, and ask for a 3-5 sentence situational briefing + alertness level (NORMAL / ELEVATED / HIGH).

**Fallback:**
```python
def _fallback(events) -> dict:
    top = max(events, key=lambda e: e.risk_score)
    return {"briefing": (
        f"Current monitoring of Bar Reef Marine Sanctuary shows {len(events)} dark-vessel "
        f"detections flagged for review. "
        f"The highest-risk detection ({top.id}) is located {top.distance_to_mpa_km:.1f} km "
        f"from the sanctuary boundary with a risk score of {top.risk_score:.2f} ({top.risk_level}). "
        f"All detections show no matching AIS broadcast within the standard 2 km / 3-hour window. "
        f"Recommended alertness level: {'HIGH' if top.risk_score >= 0.55 else 'ELEVATED'}. "
        f"A conservation officer should review the highest-risk detection as a priority."
    )}
```

---

### `agents/patrol.py` — `POST /agents/patrol`

**Input:** list of RiskEvents  
**Output:** list of `{"id", "rank", "risk_level", "distance_to_mpa_km", "justification"}`

**Deterministic fallback sort:**
1. `inside_mpa=True` first
2. `near_mpa=True` next
3. `risk_score` descending

```python
def _fallback_rank(events) -> list[dict]:
    sorted_events = sorted(
        events,
        key=lambda e: (not e.inside_mpa, not e.near_mpa, -e.risk_score)
    )
    result = []
    for i, e in enumerate(sorted_events):
        reason = "inside MPA" if e.inside_mpa else ("near MPA boundary" if e.near_mpa else "open water")
        result.append({
            "id": e.id,
            "rank": i + 1,
            "risk_level": e.risk_level,
            "distance_to_mpa_km": e.distance_to_mpa_km,
            "justification": (
                f"Risk score {e.risk_score:.2f} — unmatched AIS, {reason}, "
                f"{e.distance_to_mpa_km:.1f} km from {e.mpa_name or 'MPA'}."
            ),
        })
    return result
```

---

### `agents/ask.py` — `POST /agents/ask` (tool-calling)

**Input:** `{"question": "..."}`  
**Output:** `{"answer": "..."}`

Tools to expose to Claude:
```python
tools = [
    {
        "name": "query_detections",
        "description": "Filter risk events by source and/or risk level",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "enum": ["GFW", "YOLO_SAR"]},
                "risk_level": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]}
            }
        }
    },
    {
        "name": "get_event",
        "description": "Get a specific risk event by ID",
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"]
        }
    },
    {
        "name": "mpa_distance",
        "description": "Compute distance in km from a lat/lon to Bar Reef Marine Sanctuary",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"}
            },
            "required": ["lat", "lon"]
        }
    }
]
```

**Tool execution:**
```python
def execute_tool(name: str, inputs: dict) -> str:
    if name == "query_detections":
        events = repository.list_events(
            source=inputs.get("source"),
            risk_level=inputs.get("risk_level")
        )
        return json.dumps([e.model_dump() for e in events[:10]])
    elif name == "get_event":
        e = repository.get_event(inputs["id"])
        return json.dumps(e.model_dump() if e else {"error": "not found"})
    elif name == "mpa_distance":
        # compute haversine from (lat, lon) to Bar Reef centroid (8.4, 79.73)
        # or load the geojson and compute properly
        ...
```

**Agentic loop:** send → if response has `tool_use` blocks → execute each tool → append result → send again → extract final `text` block.

**Fallback (no API key):** simple keyword matching:
```python
def _fallback(question: str) -> str:
    q = question.lower()
    if "highest" in q or "risk" in q:
        return "The highest-risk detection is bar-reef-003 at 8.51°N 79.68°E, with a risk score of 0.61 (HIGH). It is 0.4 km from Bar Reef Marine Sanctuary and shows no matching AIS broadcast."
    if "mpa" in q or "bar reef" in q:
        return "Bar Reef Marine Sanctuary is located off the northwest coast of Sri Lanka. The nearest flagged detection (bar-reef-003) is 0.4 km from its boundary."
    return "I can answer questions about the flagged vessel detections. Try asking: 'Which detection is highest risk?' or 'How far is bar-reef-003 from the MPA?'"
```

---

## Run

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

---

## Tests

```bash
cd backend
pytest tests/ -v
```

### `tests/test_risk.py`

Import the risk function from the ML pipeline and test it:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ml"))
from pipeline.risk import calculate_risk

def test_worked_example():
    score, level = calculate_risk(0.70, False, True, False, True, 1.0)
    assert score == 0.61
    assert level == "HIGH"

def test_no_ais_data():
    score, level = calculate_risk(0.70, False, False, False, True, 1.0)
    # ais_score = 0.3 (neutral)
    assert score == round(0.30*0.70 + 0.25*0.3 + 0.25*0.6, 3)

def test_inside_mpa():
    score, level = calculate_risk(0.70, False, True, True, False, 1.0)
    # mpa_score = 1.0
    assert level == "CRITICAL" or level == "HIGH"
```

### `tests/test_endpoints.py`

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_list_risk_events():
    r = client.get("/risk-events")
    assert r.status_code == 200
    assert len(r.json()) > 0

def test_get_event():
    r = client.get("/risk-events/bar-reef-003")
    assert r.status_code == 200
    assert r.json()["risk_score"] == 0.61

def test_get_mpa():
    r = client.get("/mpa")
    assert r.status_code == 200

def test_model_metrics():
    r = client.get("/model-metrics")
    assert r.status_code == 200
    assert r.json()["map50"] == 0.838
```

---

## Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Key Rules

1. Every agent must have a deterministic fallback — demo must work with `ANTHROPIC_API_KEY` empty
2. Agents never accuse — always "flagged for review", never "is committing IUU fishing"
3. The `/risk-events/{id}/review` endpoint updates in-memory only (MVP) — restart resets it
4. CORS must allow `http://localhost:5173` for the frontend dev server
5. Do not run YOLO inference in the API — the API only serves pre-computed results from `risk_events.json`
