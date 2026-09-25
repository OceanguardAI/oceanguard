# OceanGuard AI Backend + Agents

This backend serves the ML outputs from `backend/data/` and exposes:

- risk event APIs
- GeoJSON and model metrics APIs
- deterministic review updates
- Gemini-backed agents with fallback behavior when no API key is configured

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Optional `.env` for local backend runs:

```text
copy .env.example .env
GEMINI_API_KEY=your_api_key_here
```

Without Gemini credentials, all agent routes still work through deterministic fallbacks.
For Docker runs from the repo root, use the repo-root `.env` instead; `docker-compose.yml`
forwards the same backend agent settings into the container.
For auth setup details, use `../API_SETUP.md` for the API-key path or `../GCP_GEMINI_SETUP.md`
for the Google Cloud / Vertex-style path.

## Data Files

The backend reads static files from `backend/data/`:

- `risk_events.json`
- `bar_reef.geojson`
- `metrics.json`
- `ports.json`

These should already be synchronized by the ML workflow.

## Run the API

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```powershell
curl http://localhost:8000/health
```

Agent runtime check:

```powershell
curl http://localhost:8000/agents/status
```

## Main Endpoints

### Event APIs

- `GET /health`
- `GET /detections`
- `GET /risk-events`
- `GET /risk-events/{event_id}`
- `POST /risk-events/{event_id}/review`
- `GET /risk-summary`

`/risk-events` starts with sample cases from `backend/data/risk_events.json`.
External observation-level events can be pushed through `/ingest/push`; GFW 4Wings
report cells are not inserted as vessel events.

### GFW Activity and Source Status

- `GET /activity/gfw?bbox=west,south,east,north&offset=0&limit=600`: paginated SAR activity cells in the selected area. `detection_count` is a report total, not an individual vessel identity or model confidence.
- `GET /ingest/status`: process-local last attempt, last success, sanitized error category, aggregate count, and risk-event mode.
- `POST /ingest/gfw`: refresh the process-local activity snapshot. A failed refresh keeps the last successful snapshot and marks it stale.

GFW report intervals and ingestion time are preserved separately. This slice does
not provide per-vessel acquisition time from the 4Wings report, durable activity
storage, or a scheduled refresh. A configured token alone does not prove access.

`GET /risk-events` supports:

- `source`
- `level`
- `review_status`

### Geo + Metrics APIs

- `GET /mpa`
- `GET /ports`
- `GET /model-metrics`

### Agent APIs

Posted payload routes:

- `GET /agents/status`
- `POST /agents/narrate`
- `POST /agents/briefing`
- `POST /agents/patrol`
- `POST /agents/ask`

Repo-backed convenience routes:

- `POST /agents/narrate/{event_id}`
- `POST /agents/briefing/current`
- `POST /agents/patrol/current`

The repo-backed briefing and patrol routes also accept:

- `source`
- `level`
- `review_status`

## Backend Behavior

### Review persistence

Review updates are written back to `backend/data/risk_events.json`, so:

- `Pending`
- `Confirmed Risk`
- `False Positive`
- `Resolved`

survive process restarts.

### Risk summary

`GET /risk-summary` returns:

- total event count
- source counts
- risk-level counts
- review-status counts
- inside/near-MPA counts
- highest-risk event id and score

### Ask agent fallback topics

Without a Gemini key, `POST /agents/ask` can still answer questions about:

- highest-risk detection
- total counts
- high/critical counts
- model metrics
- port data
- review-state counts

## Tests

Run the backend suite:

```powershell
python -m pytest tests -q
```

Current expected result after the latest backend slice:

- all backend tests pass
- review updates persist on disk
- `risk-summary` resolves from loaded backend data
- repo-backed agent routes work without an API key
