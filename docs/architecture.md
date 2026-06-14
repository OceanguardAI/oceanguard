# OceanGuard AI — System Architecture

## Overview

OceanGuard is a three-tier decision-support system. The ML pipeline (offline, heavy) is decoupled from the API (stateless, fast) which is decoupled from the UI. Each tier can be developed, tested, and deployed independently.

---

## Architecture Diagram

```
────────────────────────────────────────────────────────────────────────
                       DATA SOURCES (external)
  Sentinel-1 SAR scenes   Global Fishing Watch   WDPA      OSM
  (xView3 / Copernicus)   (dark-vessel + AIS)  (MPA polys) (ports)
────────────────────────┬────────────────────┬──────────────┬───────────
                        │                    │              │
                        ▼                    ▼              ▼
────────────────────────────────────────────────────────────────────────
         ML PIPELINE  (offline / batch — Python modules)

  tiling.py ──► detect.py ──► georeference.py
  (SAR→640px)  (YOLO best.pt) (pixel→lat/lon, pyproj/rasterio)
                                    │
                                    ▼
                           enrich.py
                  (MPA distance · port distance · AIS match)
                                    │
                                    ▼
                           risk.py  ←── DETERMINISTIC ENGINE
              inputs: detection conf · AIS match · MPA distance · port dist
              output: risk_score, risk_level, structured evidence
──────────────────────────────────┬─────────────────────────────────────
                                  │ writes processed artifacts
                                  ▼
                    risk_events.json / SQLite (the "store")
                                  │
                                  ▼
────────────────────────────────────────────────────────────────────────
                   BACKEND  (FastAPI — Python)

  REST API                          AGENT LAYER (Anthropic API)
  ── GET  /health                   ── POST /agents/narrate   (#1)
  ── GET  /detections               ── POST /agents/briefing  (#4)
  ── GET  /risk-events              ── POST /agents/patrol    (#5)
  ── GET  /risk-events/{id}         ── POST /agents/ask       (#2, tool-calling)
  ── POST /risk-events/{id}/review
  ── GET  /mpa
  ── GET  /ports
  ── GET  /model-metrics
──────────────────────────────────┬─────────────────────────────────────
                                  │ JSON over HTTP
                                  ▼
────────────────────────────────────────────────────────────────────────
              FRONTEND  (React + Vite + Tailwind)

  Map Dashboard ── Evidence Cards ── Ask OceanGuard ── Daily Briefing
  Patrol Board ── Data Sources ── Model Metrics ── Responsible-AI footer
  (react-leaflet map · recharts metrics · lucide icons)
────────────────────────────────────────────────────────────────────────
                                  │
                                  ▼
                     Conservation Officer (decides)
```

---

## Design Decisions

### 1. Deterministic Core + AI Explanation Layer

The risk score and risk level are computed by a deterministic function (`risk.py`) with explicit weights and thresholds. Claude is used only to explain the result in plain language — it never changes the score.

**Why this matters:** An enforcement authority needs to be able to answer "why did this get flagged?" with a traceable audit trail. A neural network answering that question is not auditable. A weighted formula is.

### 2. Right-Sized Persistence

The demo dataset is ~126 events. JSON in memory is perfectly adequate. The architecture documents the exact upgrade path to SQLite (for hundreds of thousands of events) and then PostGIS (for spatial queries at scale) — signalling awareness of when to add complexity.

**Upgrade path:**
- JSON (MVP, ~100s of events) → already in `store/repository.py`
- SQLite (thousands of events) → swap `repository.py` to use `aiosqlite`
- PostgreSQL + PostGIS (millions of events, spatial queries) → add `asyncpg` + spatial indices

### 3. Offline ML + Online API

The ML pipeline (tiling, detection, georeferencing) is a separate offline batch job. The API never runs YOLO inference on request — it serves pre-computed results. This means:

- The API has no GPU dependency and can run anywhere
- Detection can be re-run on new scenes without touching the API
- Results are reproducible and storable

### 4. Twelve-Factor Friendly

- Config via environment variables (`ANTHROPIC_API_KEY`, `GFW_TOKEN`)
- No secrets in code
- Docker containers for both services
- Stateless API (any instance serves any request)

### 5. Two-Proof Narrative (why two data sources)

The xView3 SAR scene and the GFW dark-vessel data are complementary, not redundant:

| | xView3 / YOLO | GFW Dark Vessels |
|---|---|---|
| Geography | Gulf of Guinea (global scene) | Bar Reef, Sri Lanka |
| Purpose | Proves the detector works on real SAR | Proves the risk framework flags real threats |
| UI location | Model Metrics page | Map Dashboard (headline demo) |
| Source | Our own YOLO11n inference | GFW public API (SAR-derived) |

Merging them on the same map would be misleading. Presenting them separately, each with its own framing, is honest and stronger.

---

## Data Flow (per request)

### Map load
```
GET /mpa         → bar_reef.geojson → Leaflet Polygon (teal)
GET /risk-events?source=GFW → 4 events → Leaflet CircleMarkers (risk-colored)
GET /model-metrics → metrics.json → recharts on Metrics page
```

### Click a marker → Evidence Card
```
UI has the event already (from /risk-events)
→ POST /agents/narrate  { event }
  → narrator.py calls Anthropic API (or fallback)
  → returns { why_flagged, uncertainty }
  → displayed in Evidence Card
```

### Review button
```
POST /risk-events/{id}/review  { review_status: "Confirmed Risk" }
→ repository.py updates in-memory store
→ UI optimistically updates badge
```

### Ask OceanGuard
```
POST /agents/ask  { question: "Which is highest risk?" }
→ ask.py sends to Claude with tools
→ Claude calls query_detections({ risk_level: "HIGH" })
→ ask.py executes tool, returns event list
→ Claude reads result, answers in plain English
→ displayed in chat thread
```

---

## Component Responsibilities

| Component | Responsibility | Does NOT do |
|---|---|---|
| `tiling.py` | SAR GeoTIFF → 640px PNG tiles | Inference |
| `detect.py` | YOLO inference over tiles | Georeferencing |
| `georeference.py` | Pixel coords → WGS84 lat/lon | Enrichment |
| `enrich.py` | MPA distance, port distance, AIS check | Risk scoring |
| `risk.py` | Deterministic risk score + level | Explanation |
| `build_risk_events.py` | Orchestrates pipeline → JSON | Serving |
| `repository.py` | In-memory store, CRUD | Business logic |
| `narrator.py` | Plain-language explanation via Claude | Risk scoring |
| `briefing.py` | Situational summary via Claude | Individual event detail |
| `patrol.py` | Priority ranking via Claude | Scoring |
| `ask.py` | Tool-calling Q&A via Claude | Serving events directly |
| `MapView.tsx` | Leaflet map + marker interaction | Sidebar content |
| `EvidenceCard.tsx` | Full event detail + review | Map rendering |

---

## Deployment Targets

| Service | Local | Production |
|---|---|---|
| Backend | `uvicorn app.main:app --reload` | Google Cloud Run |
| Frontend | `npm run dev` | Vercel / Netlify |
| Full stack | `docker-compose up` | Cloud Run + CDN |

The backend container is stateless (data files are mounted volumes in production). The frontend is a static build served by nginx.
