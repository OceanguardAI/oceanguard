# OceanGuard AI Project Guide

## 1. What this project is

OceanGuard AI is a maritime monitoring and decision-support system.

Its job is to help a conservation officer answer questions like:

- Which vessel detections are most suspicious right now?
- Which of those detections are near or inside a protected marine area?
- Do we have a fresh SAR image for that location?
- If I click a point on the map, what does the latest available radar pass show there?
- Which detections should be reviewed or patrolled first?

The key product idea is simple:

- radar can see vessels even when they are not broadcasting AIS
- protected-area context changes how suspicious a vessel is
- a human needs a ranked queue, visual evidence, and a plain-language explanation

OceanGuard turns those three needs into one workflow.

## 2. The main product features

The current system is built around these feature groups:

### A. Live detection monitoring

- Ingests SAR-based vessel detections from Global Fishing Watch.
- Converts them into `RiskEvent` objects.
- Scores and ranks them.
- Shows them on the dashboard map and queue.

### B. Spatial protected-area intelligence

- Loads Marine Protected Area boundaries.
- Computes whether a detection is inside an MPA or near one.
- Uses that proximity as a major input into the risk score.
- Serves only viewport-relevant polygons to the frontend.

### C. Live SAR evidence

- Fetches actual Sentinel-1 SAR chips on demand.
- Displays them in the Evidence Card.
- Lets users run their own verification at a selected point.

### D. On-demand YOLO verification

- Uses a separate model-serving service.
- Runs over the latest SAR chip for a single point.
- Or tiles a visible area and sweeps the whole region.
- Compares results against existing known detections.

### E. AI explanation layer

- Gemini explains why detections were flagged.
- Gemini can summarize current conditions.
- Gemini can rank patrol priorities.
- Gemini can answer officer questions through a tool-backed assistant.

### F. Frontend operations console

- Dashboard map
- Detection queue
- Evidence Card
- Daily briefing
- Patrol recommendations
- Ask OceanGuard assistant
- Metrics and data-source views
- Landing page for presentation/demo use

### G. Offline ML workflow

- Builds detection-derived output artifacts.
- Validates models and artifacts.
- Syncs outputs into the backend handoff directory.

### H. Cloud deployment

- Backend deployed to Cloud Run
- Frontend deployed to Cloud Run
- YOLO service deployed separately to Cloud Run
- GitHub Actions builds and deploys containers

## 3. The design philosophy

OceanGuard is intentionally split into layers.

This is one of the most important things to understand in the repo.

### Deterministic core first

The risk score itself is deterministic.

That means:

- the inputs are explicit
- the weights are explicit
- the thresholds are explicit
- the result can be audited and reproduced

This is critical because the product is decision support, not a black-box enforcement system.

### AI only explains, ranks, and helps navigate

Gemini does not decide guilt.

Instead it:

- explains
- summarizes
- prioritizes
- answers questions

When Gemini is unavailable, the app still works using deterministic fallbacks.

### Model serving is separated from the API

Torch and YOLO run in a different Cloud Run service from the main API.

That keeps:

- the API lighter
- cold starts more manageable
- failure domains separated

### Live data and offline artifacts both matter

This project combines:

- live operational paths
- offline ML artifact generation

That means the repo is not just "a backend with a frontend" and not just "an ML project."

It is both.

## 4. How a normal user session works

Here is the easiest mental model for the full product lifecycle.

### Step 1. Backend starts

The backend loads seed data from `backend/data/risk_events.json`.

Then, in the background:

- it loads the MPA index
- it may ingest live GFW detections
- live data can replace the seed set in memory

This is done in the background so Cloud Run health checks pass quickly.

### Step 2. Frontend opens the dashboard

The frontend requests:

- risk events
- MPA overlays
- metrics when needed

The dashboard immediately renders either:

- live/seed data, or
- a connecting state while live ingest finishes

### Step 3. Officer reviews detections

The user can:

- click a detection on the map
- select it from the detection queue
- open the Evidence Card
- read the agent explanation
- review status
- run YOLO verification

### Step 4. Officer explores arbitrary locations

The user can:

- activate point scan
- click a coordinate on the map
- run fresh SAR verification there

Or:

- move the map to an area of interest
- trigger area sweep
- receive confirmed vs new contacts

### Step 5. Officer asks for support

The user can:

- read a daily briefing
- view patrol suggestions
- ask the assistant questions like:
  - what is highest risk?
  - how is the score calculated?
  - which detections are inside an MPA?

## 5. What "live" means in this project

This project uses the word "live" in multiple ways, and learning that distinction matters.

### Live detections

Global Fishing Watch detections are fetched from an external API at runtime.

### Live SAR chips

Sentinel-1 chips are fetched on demand from Sentinel Hub/CDSE.

### Live point verification

When a user clicks a point, the system fetches a fresh SAR chip for that point and runs YOLO at request time.

### Live sweep

When a user sweeps an area, the system tiles the visible region and runs multiple fresh point detections.

### Not live video

This is not a continuous satellite video stream.

It is the latest available radar pass processed on demand.

## 6. How the repo is organized conceptually

The repo is easiest to understand in six zones.

### `frontend/`

All browser UI logic:

- landing page
- dashboard shell
- map view
- evidence panel
- assistant
- patrol and briefing views

### `backend/app/api/routes/`

HTTP entrypoints:

- events
- geo data
- ingest
- SAR chip routes
- YOLO verification routes
- agents
- metrics

### `backend/app/services/`

Operational business logic:

- GFW ingest
- AIS sampling
- MPA indexing
- Sentinel SAR chip fetching

### `backend/app/agents/`

Gemini-based explanation and assistant logic:

- narrator
- briefing
- patrol
- ask
- Gemini client

### `backend/app/store/`

In-memory repository for current live/seed event state.

### `ml/`

Offline workflow for:

- validating artifacts
- generating outputs
- syncing outputs into backend handoff format

### `yolo-service/`

Independent inference microservice for:

- fetching tight SAR chips
- loading the trained YOLO model
- running detections

## 7. The most important technical decisions

### Decision 1. Use GFW as the global live feed

This gives the system a realistic operational dataset immediately.

OceanGuard does not need to generate every global detection itself.

Instead:

- GFW provides global SAR detections
- OceanGuard adds its own scoring, SAR chip access, explanation layer, and verification tools

### Decision 2. Use deterministic scoring

The score is designed for traceability, not novelty.

That makes it easier to:

- explain to users
- document
- test
- defend in operational reviews

### Decision 3. Use a separate YOLO service

This keeps the main API responsive and simpler.

### Decision 4. Keep the repository in memory

This is fast and easy for hackathon/demo use, but it is not long-term persistence.

It is an explicit product tradeoff.

### Decision 5. Serve MPA data by viewport

The full WDPA set is too large to dump into the browser all at once.

So the system:

- keeps a full spatial index backend-side
- returns only the polygons that intersect the current map view

## 8. Best way to learn the code

If you want to deeply understand the repo, follow one feature at a time.

### Good learning path

1. Read `CODEBASE_MAP.md`
2. Trace dashboard load
   - frontend fetch
   - backend route
   - repository response
3. Trace one detection click
   - selection state
   - Evidence Card
   - narrator agent
4. Trace point scan
   - map click
   - verify route
   - YOLO service
5. Trace area sweep
   - viewport bounds
   - backend tiling
   - map contact rendering
6. Trace one cloud deployment workflow
   - build
   - push
   - deploy

## 9. Documents you should read next

- `CODEBASE_MAP.md`
- `modules/dashboard-and-interface.md`
- `modules/live-ingestion-and-risk-scoring.md`
- `modules/spatial-intelligence-and-protected-areas.md`
- `live-sar-and-user-selection-flow.md`
- `modules/agents-and-explanations.md`
- `modules/ml-pipeline-and-models.md`
- `modules/deployment-and-runtime.md`

## 10. Bottom line

OceanGuard is best understood as:

- a live detection intake layer
- a deterministic spatial/risk reasoning engine
- an on-demand SAR verification system
- a model-serving sidecar
- an AI explanation interface
- a polished operator dashboard

Once you see those as separate modules, the whole repo becomes much easier to learn and extend.
