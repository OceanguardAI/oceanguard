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
- `GET /risk-events/{event_id}/reviews`
- `GET /risk-summary`

`/risk-events` starts with sample cases from `backend/data/risk_events.json`.
External observation-level events can be pushed through `/ingest/push`; GFW 4Wings
report cells are not inserted as vessel events.

### GFW Activity and Source Status

- `GET /activity/gfw?bbox=west,south,east,north&offset=0&limit=600`: paginated SAR activity cells in the selected area. `detection_count` is a report total, not an individual vessel identity or model confidence.
- `GET /ingest/status`: last attempt, last success, sanitized error category, aggregate count, storage scope, and risk-event mode.
- `POST /ingest/gfw`: refresh the activity snapshot. A failed refresh keeps the last successful snapshot and marks it stale.

GFW report intervals and ingestion time are preserved separately. This slice does
not provide per-vessel acquisition time from the 4Wings report or a scheduled
refresh. A configured token alone does not prove access.

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

Without `DATABASE_URL`, sample cases and reviews use the local JSON/process store.
The case status is written to `backend/data/risk_events.json`; review history is
process-local. This is not durable across Cloud Run instances or deployments.

With `DATABASE_URL`, cases, complete GFW activity snapshots, and append-only
review history use PostgreSQL/PostGIS. The application does not import sample
cases into a new database. External observation-level cases enter through
`POST /ingest/push?mode=merge`. `mode=replace` is rejected in database mode to
protect review history. IDs are insert-only in database mode: reusing an ID
cannot overwrite a previous observation or its review. Review records have no
analyst identity until authentication is implemented.

Valid review states are:

- `Pending`
- `Confirmed Risk`
- `False Positive`
- `Resolved`

The PostgreSQL path requires a database with PostGIS available and migrations
applied before the API starts:

```powershell
cd backend
$env:DATABASE_URL = '<connection string from your secret store>'
.\.venv\Scripts\python.exe -m app.store.migrate
```

On Cloud Run, provide `DATABASE_URL` through Secret Manager and grant the runtime
identity access to that secret and the Cloud SQL instance. Do not put the
connection string in GitHub variables or source files. Migrations need a role
permitted to install the PostGIS extension; the runtime identity can use a
more restricted database role. Database mode is not validated against a live
Cloud SQL instance yet, and should be tested before enabling it in production.
The dedicated database integration test is opt-in and writes test records:

```powershell
$env:OCEANGUARD_TEST_DATABASE_URL = '<dedicated disposable PostGIS database>'
.\.venv\Scripts\python.exe -m pytest -q tests/test_postgres_integration.py
```

Do not point that test at production. Database-backed review and ingest routes
still need authenticated access before production use. Snapshot retention and
backup/restore drills are also pending.

### Durable GFW refresh jobs

After applying migrations with `DATABASE_URL` set, a separate worker can run a
bounded GFW refresh. It does not require the API container to stay alive during
the fetch. The same daily key enqueues only one job; provide a distinct key for
an intentional re-run. A job may be retried after a provider failure or a lost
worker lease, up to five attempts. Snapshot publication and job completion are
one transaction, so an expired worker cannot publish over a newer claim.

```powershell
cd backend
python -m app.store.migrate
python -m app.jobs.cli enqueue-gfw
python -m app.jobs.cli run-once
```

`run-once` handles at most one ready job, then exits. A scheduler must invoke
the enqueue command daily and the worker command repeatedly to process retries;
neither schedule nor a Cloud Run Job is configured by this code slice. Keep
`GFW_API_TOKEN` in a managed secret, not in source control. The existing
startup refresh and manual API path still operate independently until the
queue has been validated against a live database and worker deployment. A
provider or storage failure exits nonzero; the job remains queued for a later
run unless its attempt limit was reached.

### Source status

GET /sources/status is the single read-only source readiness view. It never
returns provider credentials. A source being configured only means the
required key or URL is present; it does not prove that the provider is
reachable or that the requested area has coverage. GFW activity, AIS samples,
Sentinel-1 imagery, and YOLO inference retain their distinct limitations.

### Operational records

The versioned read APIs are available under `/v1` after migrations and a
PostGIS database are configured:

- `/v1/observations`
- `/v1/tracks` and `/v1/tracks/{id}/points`
- `/v1/alerts`

Local demo mode returns `503 Operational database is not configured` for these
endpoints rather than pretending that sample risk events are durable tracks.
The write path is reserved for workers and authenticated ingestion adapters;
these APIs do not yet make the public demo mutation-capable.

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
