# OceanGuard AI — System Architecture

## Overview

OceanGuard is a four-tier decision-support system. The ML pipeline (offline, batch) is decoupled from the live ingestion layer, which is decoupled from the API, which is decoupled from the UI. Each tier can be developed, tested, and deployed independently.

---

## Architecture Diagram

```
────────────────────────────────────────────────────────────────────────
                       DATA SOURCES (external)
  Global Fishing Watch    AISStream.io     WDPA (UNEP-WCMC)   OSM
  (SAR dark-vessel API)   (Live AIS WS)    (open ArcGIS)      (ports)
         │                     │                 │               │
         ▼                     ▼                 ▼               ▼
────────────────────────────────────────────────────────────────────────
         LIVE INGESTION LAYER  (backend startup + on-demand)

  gfw_ingest.py        ais_stream.py       mpa_index.py
  POST /ingest/gfw     POST /ais/verify-dark  GET /mpa
  (SAR detections      (AIS cross-check     (polygon layer +
   + AIS cross-match    dark confirmed)      spatial scoring)
   from GFW API)
────────────────────────────────────────────────────────────────────────
         ML PIPELINE  (offline / batch — Python modules in ml/)

  fetch_sentinel1.py ──► run_inference_from_tif.py ──► georeference
  (Sentinel-1 GRD)      (YOLO11n best.pt)             (pyproj/rasterio)
                                    │
                                    ▼
                           build_risk_events.py
                  (MPA distance · AIS match · risk formula)
                                    │
                                    ▼
                         outputs/risk_events.json  ──► backend/data/
──────────────────────────────────┬─────────────────────────────────────
                                  │ in-memory store (repository.py)
                                  ▼
────────────────────────────────────────────────────────────────────────
                   BACKEND  (FastAPI — Python, Google Cloud Run)

  Core REST                           Live Ingestion
  ── GET  /health                     ── GET  /ingest/status
  ── GET  /risk-events                ── POST /ingest/gfw
  ── GET  /risk-events/{id}           ── GET  /ais/live
  ── POST /risk-events/{id}/review    ── POST /ais/verify-dark
  ── GET  /mpa
  ── GET  /mpa/status                 YOLO Verification (shipped)
  ── GET  /ports                      ── GET  /verify/yolo/status
  ── GET  /model-metrics              ── POST /verify/yolo
                                      ── POST /verify/yolo/sweep
  AI Agents (Gemini 2.5 Flash)
  ── POST /agents/narrate
  ── POST /agents/briefing
  ── POST /agents/patrol
  ── POST /agents/ask
──────────────────────────────────┬─────────────────────────────────────
                                  │ JSON over HTTP
                                  ▼
────────────────────────────────────────────────────────────────────────
              FRONTEND  (React 18 + Vite + TypeScript + Tailwind)

  Landing Page (/)
  ── Hero video, HUD overlay, BlindSpotVisual, EvidenceCardMock
  ── How It Works, CTA

  Dashboard (/dashboard)
  ── MapView (Leaflet) — color-coded vessel dots, scan mode, sweep mode
  ── EvidenceCard — per-detection detail + YOLO verify button
  ── DailyBriefing — Gemini executive summary
  ── PatrolBoard — AI-ranked top 3 patrol locations
  ── RiskTable — all events, review actions
  ── AskOceanGuard — conversational Q&A
  ── ModelMetrics — YOLO training stats + validation
  ── DataSources — provenance reference
────────────────────────────────────────────────────────────────────────
                                  │
                                  ▼
                     Conservation Officer (decides)
```

---

## Design Decisions

### 1. Deterministic Core + AI Explanation Layer

The risk score and risk level are computed by a deterministic function with explicit weights and thresholds. Gemini 2.5 Flash is used only to explain the result in plain language — it never changes the score.

**Why this matters:** An enforcement authority needs to answer "why did this get flagged?" with a traceable audit trail. A deterministic additive formula is auditable; a neural network output is not.

### 2. GFW as Primary Detection Feed

The live system uses the Global Fishing Watch SAR API as its primary detection source. GFW does the Sentinel-1 SAR processing and AIS cross-matching server-side. OceanGuard ingests the pre-processed results at startup (`GFW_INGEST_ON_STARTUP=true`) and applies its own risk scoring on top.

**YOLO is on-demand only.** The YOLO service runs when an officer clicks "Run YOLO Check" (single point) or "Sweep Area" (viewport grid). It is not the primary detection pipeline.

### 3. YOLO Verification — Two Modes (both shipped)

```
POST /verify/yolo         → single-point confirm (lat/lon/date → Sentinel-1 chip → YOLO)
POST /verify/yolo/sweep   → area sweep (bbox tiled at ~0.04°, max 12 tiles, 4 parallel workers)
```

Sweep contacts are classified:
- **teal diamond** — confirmed (matches a known GFW detection within 2 km)
- **red pulsing diamond** — new (no known detection nearby → dark-vessel candidate the GFW feed missed)

Agreement boost: when YOLO confirms a GFW detection, `risk_score += 0.10`.

### 4. Right-Sized Persistence

The live store is in-memory (repository.py). Reviews written via `POST /risk-events/{id}/review` are in-memory only (`persist=False`) to preserve the seed file as offline fallback. Upgrade path: JSON → SQLite → PostgreSQL+PostGIS.

### 5. Twelve-Factor Friendly

- Config via environment variables only (never hardcoded)
- Secrets in `.env` (local) and GitHub Secrets (Cloud Run)
- Stateless API containers — any instance serves any request
- Push-to-main auto-deploys via GitHub Actions → Cloud Run

---

## AI Agent Layer (Gemini 2.5 Flash)

All four agents use `gemini-2.5-flash` via the Google GenAI SDK. The model ID is set in `backend/app/core/config.py` as `gemini_model = "gemini-2.5-flash"`.

| Agent | Route | What it does |
|---|---|---|
| Narrator | `POST /agents/narrate` | Explains why a single detection was flagged, in plain English |
| Briefing | `POST /agents/briefing` | Writes a 2–4 sentence executive summary of all current events |
| Patrol | `POST /agents/patrol` | Ranks top 3 detections by patrol urgency with justification |
| Ask | `POST /agents/ask` | Tool-calling Q&A — answers officer questions about live data |

**Reliability boundary:** Each agent has a deterministic fallback. If Gemini is unavailable, the UI still returns useful output. Gemini explains scores; it never sets them.

---

## Data Flow (per request)

### Dashboard load
```
GET /risk-events          → live GFW detections → Leaflet CircleMarkers (risk-colored dots)
GET /mpa                  → WDPA FeatureCollection → Leaflet Polygon overlay
GET /model-metrics        → metrics.json → recharts on Metrics page
GET /ingest/status        → feed config + event counts
```

### Click a detection → Evidence Card
```
UI already has the event (from /risk-events)
→ POST /agents/narrate  { event }
  → narrator.py calls Gemini (or fallback)
  → returns { why_flagged, uncertainty }
  → displayed in Evidence Card
```

### Run YOLO Check (single point)
```
POST /verify/yolo?lat=&lon=&date=&event_id=
→ verify.py fetches Sentinel-1 chip via Sentinel Hub/CDSE
→ calls oceanguard-yolo service → YOLO inference
→ if found + event_id: risk_score += 0.10 in store
→ returns { agreement, yolo: { found, chip_png_b64, detections, best_confidence } }
→ YoloResultView.tsx renders the SAR chip with bounding boxes
```

### Sweep Area
```
POST /verify/yolo/sweep?min_lon=&min_lat=&max_lon=&max_lat=&date=
→ verify.py tiles bbox into ≤12 chips (0.04° spacing)
→ 4 parallel YOLO workers
→ each contact classified: confirmed (≤2 km from known) or new
→ map shows teal/red diamond markers
```

### Review button
```
POST /risk-events/{id}/review  { review_status: "Confirmed Risk" }
→ repository.py updates in-memory store (persist=False)
→ UI optimistically updates badge
```

### Ask OceanGuard
```
POST /agents/ask  { question: "Which is highest risk?" }
→ ask.py sends to Gemini with tool definitions
→ Gemini calls query_detections({ risk_level: "HIGH" })
→ ask.py executes tool, returns event list
→ Gemini reads result, answers in plain English
```

---

## Component Responsibilities

| Component | Responsibility | Does NOT do |
|---|---|---|
| `gfw_ingest.py` | Pull SAR detections from GFW API at startup | AIS broadcasts |
| `ais_stream.py` | WebSocket AIS feed, dark-vessel cross-check | Risk scoring |
| `mpa_index.py` | Shapely STRtree spatial lookup for MPA distance | Serving polygons |
| `repository.py` | In-memory store, CRUD, upsert | Business logic |
| `narrator.py` | Plain-language explanation via Gemini | Risk scoring |
| `briefing.py` | Situational summary via Gemini | Individual event detail |
| `patrol.py` | Priority ranking via Gemini | Scoring |
| `ask.py` | Tool-calling Q&A via Gemini | Serving events directly |
| `verify.py` | YOLO point + sweep endpoints, agreement boost | Primary detection |
| `MapView.tsx` | Leaflet map, scan mode, sweep mode, bounds reporting | Sidebar content |
| `EvidenceCard.tsx` | Full event detail, YOLO verify trigger, review | Map rendering |
| `YoloResultView.tsx` | Renders SAR chip + YOLO bounding boxes | Triggering YOLO |
| `DailyBriefing.tsx` | Fetches + displays Gemini briefing | Agent logic |
| `PatrolBoard.tsx` | Fetches + displays Gemini patrol ranking | Map interaction |
| `AskOceanGuard.tsx` | Chat interface for Gemini Q&A | Agent logic |

---

## Deployment

| Service | Local | Production |
|---|---|---|
| Backend | `uvicorn app.main:app --reload --port 8000` | Google Cloud Run (auto-deploy on push to main) |
| YOLO service | separate FastAPI + torch container | Google Cloud Run (separate service) |
| Frontend | `npm run dev` | Google Cloud Run (nginx static) |
| Full stack | `docker-compose up` | GitHub Actions → Cloud Run |

Push to `main` branch triggers GitHub Actions CI/CD → builds Docker images → pushes to Artifact Registry → deploys to Cloud Run.

Credentials: `GFW_API_TOKEN`, `AISSTREAM_API_KEY`, `SENTINELHUB_CLIENT_ID`, `SENTINELHUB_CLIENT_SECRET`, `GEMINI_API_KEY` — all in GitHub Secrets, never in code.
