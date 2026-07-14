# OceanGuard AI Codebase Map

This document answers one practical question:

"If I want to understand or change feature X, which files should I open first?"

---

## 1. Top-level map

```text
OceanEye/
├── backend/          FastAPI API, live ingest, agents, repository
├── frontend/         React + Vite operator UI
├── ml/               Offline ML workflow and artifact generation
├── yolo-service/     Separate model-serving API for on-demand SAR verification
├── docs/             Architecture and feature references
└── .github/workflows/ Cloud deployment pipelines
```

---

## 2. Backend map

### `backend/app/main.py`

Open this first when you want to understand backend startup behavior.

It shows:

- FastAPI app creation
- router registration
- CORS setup
- lifespan startup logic
- background GFW ingest kickoff

### `backend/app/api/routes/`

This folder is the public API surface.

#### `events.py`

Use for:

- listing detections
- reading one event
- review status updates
- summary endpoints

#### `geo.py`

Use for:

- MPAs
- MPA status
- ports

#### `ingest.py`

Use for:

- GFW ingest status
- manual ingest trigger
- externally pushed event merge/replace

#### `sar.py`

Use for:

- evidence-card SAR chip requests
- SAR configuration status

#### `verify.py`

Use for:

- point scan
- area sweep
- YOLO agreement boost behavior

#### `agents.py`

Use for:

- narrator
- briefing
- patrol ranking
- ask assistant
- agent status

#### `metrics.py`

Use for:

- model metrics returned to the frontend

#### `ais.py`

Use for:

- live AIS sampling and dark-vessel confirmation flow

### `backend/app/services/`

This folder holds the operational logic behind the routes.

#### `gfw_ingest.py`

Open when learning:

- live global detection fetch
- raw GFW payload parsing
- `RiskEvent` creation
- ranking and stratified sampling

#### `ais_stream.py`

Open when learning:

- short-window AIS sampling
- AISStream bounding-box subscription
- nearest broadcast confirmation logic

#### `mpa_index.py`

Open when learning:

- MPA loading
- STRtree usage
- nearest protected area calculations
- viewport-filtered polygon serving

#### `sentinel_sar.py`

Open when learning:

- how the backend fetches a wide SAR chip for human viewing
- OAuth token reuse
- Process API request shape

### `backend/app/agents/`

This folder is the explanation/assistant layer.

#### `client.py`

Open first for Gemini integration.

It decides:

- API-key mode vs GCP/Vertex mode
- client singleton construction
- availability logic

#### `narrator.py`

One-event explanation flow.

#### `briefing.py`

Current detection set -> executive summary.

#### `patrol.py`

Current detection set -> recommended patrol list.

#### `ask.py`

The richest agent file.

Use it to understand:

- embedded system knowledge
- live dataset snapshot injection
- tool declarations
- tool execution
- deterministic fallback answers

#### `helpers.py`

Shared parsing/prompt utilities for the agent layer.

### `backend/app/store/repository.py`

This is the working in-memory data store.

Open it when learning:

- where current events live
- how merge vs replace behaves
- how review updates are stored
- why the app can operate on seed data plus live replacement

### `backend/app/models/schemas.py`

Open it when you need the canonical backend data shapes.

This is where types such as `RiskEvent`, `RiskSummary`, and agent response models are defined.

### `backend/app/core/config.py`

Open this whenever you need to understand:

- environment variables
- cloud/runtime config
- integration dependencies
- defaults

---

## 3. Frontend map

### `frontend/src/App.tsx`

This is the main frontend control tower.

Open it first when learning:

- page switching (`landing` vs `dashboard`)
- tab switching
- polling
- selection state
- evidence/assistant/scan/sweep panel precedence
- mobile responsiveness

### `frontend/src/lib/api.ts`

This is the frontend-to-backend contract layer.

Open it when learning:

- which route the frontend calls
- what arguments are passed
- how API URLs are built

### `frontend/src/components/`

Feature components live here.

#### `LandingPage.tsx`

Presentation and demo entry surface.

#### `MapView.tsx`

Core map logic:

- rendering event markers
- MPA polygon fetching
- point scan click handling
- viewport bounds reporting
- sweep contact markers

#### `EvidenceCard.tsx`

Core detail panel:

- SAR chip image
- narrator output
- YOLO verification
- review actions

#### `RiskTable.tsx`

Detection queue / list view.

#### `DailyBriefing.tsx`

Agent-powered summary panel.

#### `PatrolBoard.tsx`

Agent-powered patrol prioritization.

#### `AskOceanGuard.tsx`

Tool-backed assistant chat UI.

#### `ModelMetrics.tsx`

Model metrics rendering.

#### `DataSources.tsx`

Data provenance and system-source explanation.

#### `YoloResultView.tsx`

Shows the exact SAR chip analyzed by the YOLO service with bounding boxes drawn over it.

### `frontend/src/components/landing/`

This folder holds the landing-page-specific visuals and sections.

Use it when changing:

- hero motion
- preview cards
- blind-spot visuals
- navigation
- system storytelling blocks

### `frontend/src/components/ui/`

Reusable UI building blocks:

- buttons
- badges
- glass cards
- animated numbers
- tooltips

### `frontend/src/types/index.ts`

Frontend data-shape definitions for backend responses.

---

## 4. ML folder map

### `ml/README.md`

Start here for the offline ML flow.

### `ml/run_full_ml_workflow.py`

Main orchestration script for:

- artifact validation
- optional model validation
- event building
- backend sync
- final summary

### `ml/build_risk_events.py`

Creates final `risk_events.json`.

### `ml/pipeline/`

Core submodules of the offline workflow:

#### `detect.py`

Model inference helpers for raw SAR inputs.

#### `georeference.py`

Maps detections back into geographic space.

#### `enrich.py`

Adds spatial/contextual metadata.

#### `risk.py`

Deterministic offline risk formula.

#### `tiling.py`

Prepares SAR scenes for model input.

### `ml/validate_artifacts.py`

Checks whether expected inputs/outputs are present and sane.

### `ml/validate_model.py`

Confirms that the model artifact can be loaded.

### `ml/sync_outputs_to_backend.py`

Copies outputs into `backend/data/`.

### `ml/tests/`

Offline ML verification suite.

Use this when you want to understand what behavior the repo considers important enough to test.

---

## 5. YOLO service map

### `yolo-service/app/main.py`

Start here for the separate inference service.

It shows:

- service startup
- model warm-up
- `/health`
- `/detect-point`

### `yolo-service/app/sentinel.py`

Tight SAR chip fetch logic for model inference.

This differs from the backend display chip:

- tighter area
- denser resolution
- optimized for the model, not for human overview

### `yolo-service/app/inference.py`

Core model-serving logic:

- model singleton
- PIL/NumPy image handling
- Ultralytics inference
- pixel bbox -> lat/lon conversion

### `yolo-service/app/config.py`

Inference-service runtime config:

- model path
- confidence threshold
- chip size
- Sentinel Hub credentials

---

## 6. Deployment map

### `.github/workflows/deploy-backend.yml`

Backend image build + Cloud Run deploy.

### `.github/workflows/deploy-frontend.yml`

Frontend static build container + Cloud Run deploy.

### `.github/workflows/deploy-yolo.yml`

YOLO model-serving service build + Cloud Run deploy.

### `backend/Dockerfile`

Backend container image definition.

### `frontend/Dockerfile`

Frontend production container.

### `frontend/nginx.conf`

Frontend runtime web-server config for Cloud Run.

### `yolo-service/Dockerfile`

YOLO service production image.

---

## 7. If you want to change X, start here

### "I want to change the detection list"

Start with:

- `frontend/src/components/RiskTable.tsx`
- `frontend/src/App.tsx`
- `backend/app/api/routes/events.py`

### "I want to change how scoring works"

Start with:

- `backend/app/services/gfw_ingest.py`
- `ml/pipeline/risk.py`
- `docs/data-dictionary.md`
- related tests in `ml/tests/` and `backend/tests/`

### "I want to change map behavior"

Start with:

- `frontend/src/components/MapView.tsx`
- `frontend/src/App.tsx`
- `backend/app/api/routes/geo.py`
- `backend/app/services/mpa_index.py`

### "I want to change live SAR behavior"

Start with:

- `frontend/src/lib/api.ts`
- `frontend/src/components/EvidenceCard.tsx`
- `backend/app/api/routes/sar.py`
- `backend/app/services/sentinel_sar.py`
- `docs/live-sar-and-user-selection-flow.md`

### "I want to change point scan or sweep"

Start with:

- `frontend/src/App.tsx`
- `frontend/src/components/MapView.tsx`
- `backend/app/api/routes/verify.py`
- `yolo-service/app/main.py`
- `yolo-service/app/sentinel.py`
- `yolo-service/app/inference.py`

### "I want to change AI explanations"

Start with:

- `backend/app/agents/narrator.py`
- `backend/app/agents/briefing.py`
- `backend/app/agents/patrol.py`
- `backend/app/agents/ask.py`
- `backend/app/agents/client.py`

### "I want to change cloud deploy/runtime"

Start with:

- `.github/workflows/deploy-backend.yml`
- `.github/workflows/deploy-frontend.yml`
- `.github/workflows/deploy-yolo.yml`
- `backend/app/core/config.py`

---

## 8. Bottom line

If you remember only one thing from this file, remember this:

- `App.tsx` is the frontend control center
- `routes/` is the backend API surface
- `services/` is the backend operational logic
- `agents/` is the Gemini layer
- `repository.py` is the current live state
- `ml/` is offline artifact generation
- `yolo-service/` is the separate model-serving runtime
