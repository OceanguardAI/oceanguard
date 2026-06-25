# OceanGuard AI — Build Plan

> Current state reference for the team. Describes what is built, how it works, and how to run it.

---

## What We Built

**Problem:** IUU (Illegal, Unreported, Unregulated) fishing costs 11–26 million tonnes of fish per year. Conservation officers watching Marine Protected Areas cannot manually cross-reference satellite radar imagery against AIS vessel broadcasts. "Dark" vessels disable their AIS — invisible to tracking systems, but still visible to satellite SAR radar.

**OceanGuard:** Automates that cross-reference. Live SAR detections from Global Fishing Watch → AIS cross-check → MPA proximity → deterministic risk score → Gemini AI explanation → human officer decides.

**Demo MPA:** Bar Reef Marine Sanctuary, Sri Lanka (28 real WDPA MPAs loaded).

**Core principle:** Deterministic, auditable risk scoring (never a black box) + Gemini narration (explains the score). The formula decides the risk level; Gemini explains it in plain English.

---

## Repository Layout

```
OceanEye/
├── BUILD_PLAN.md                  ← this file
├── LIVE_DATA.md                   ← live feed status + credentials guide
├── BEGINNER_GUIDE.md              ← start here if new to the project
├── docker-compose.yml
├── .env.example
│
├── ml/                            ← offline ML pipeline
│   ├── README.md
│   ├── requirements.txt
│   ├── models/best.pt             ← YOLO11n trained weights
│   ├── data/
│   │   ├── mpas.geojson           ← 28 WDPA marine MPAs (Sri Lanka region)
│   │   ├── bar_reef.geojson       ← single MPA fallback
│   │   └── ports.json             ← OSM port locations
│   ├── outputs/
│   │   ├── detections_scene1_georef.json   ← 122 YOLO detections (xView3)
│   │   └── risk_events.json               ← 126 events (4 GFW + 122 YOLO_SAR)
│   ├── pipeline/
│   │   ├── tiling.py
│   │   ├── detect.py
│   │   ├── georeference.py
│   │   ├── enrich.py
│   │   └── risk.py
│   ├── build_risk_events.py
│   ├── fetch_sentinel1.py
│   ├── fetch_wdpa.py
│   ├── run_live_pipeline.py       ← ⚠️ experimental (domain gap)
│   ├── run_full_ml_workflow.py
│   └── validate_artifacts.py
│
├── backend/                       ← FastAPI service (Google Cloud Run)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   ├── data/
│   │   ├── risk_events.json       ← seed data (synced from ml/outputs/)
│   │   ├── mpas.geojson           ← WDPA MPA polygons
│   │   ├── ports.json
│   │   └── metrics.json           ← real YOLO model metrics
│   └── app/
│       ├── main.py
│       ├── core/config.py         ← all settings (gemini_model, gfw_*, etc.)
│       ├── models/schemas.py      ← RiskEvent, ReviewUpdate, etc.
│       ├── store/repository.py    ← in-memory event store
│       ├── services/
│       │   ├── gfw_ingest.py      ← GFW SAR API ingestion
│       │   ├── ais_stream.py      ← AISStream.io WebSocket
│       │   ├── mpa_index.py       ← Shapely STRtree MPA lookup
│       │   └── sentinel_sar.py    ← Sentinel Hub chip fetch
│       ├── agents/
│       │   ├── client.py          ← Gemini client singleton
│       │   ├── narrator.py        ← per-detection explanation
│       │   ├── briefing.py        ← daily executive summary
│       │   ├── patrol.py          ← patrol priority ranking
│       │   └── ask.py             ← tool-calling Q&A
│       └── api/routes/
│           ├── events.py          ← GET/POST /risk-events
│           ├── ingest.py          ← GFW ingestion + status
│           ├── ais.py             ← AIS live + verify-dark
│           ├── verify.py          ← YOLO point verify + sweep
│           ├── geo.py             ← MPA + ports
│           ├── metrics.py         ← model metrics
│           └── agents.py          ← narrate, briefing, patrol, ask
│
├── frontend/                      ← React 18 + Vite + Tailwind (Cloud Run)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── public/
│   │   └── hero-video.mp4         ← landing page hero video
│   └── src/
│       ├── App.tsx                ← routing: / (landing) + /dashboard
│       ├── lib/api.ts             ← all API calls
│       ├── types/index.ts         ← TypeScript types
│       └── components/
│           ├── LandingPage.tsx    ← hero, blind spot, pipeline, CTA
│           ├── landing/
│           │   ├── LandingNavbar.tsx
│           │   ├── HeroAnimation.tsx
│           │   ├── HudOverlay.tsx
│           │   ├── BlindSpotVisual.tsx
│           │   ├── EvidenceCardMock.tsx
│           │   └── HowItWorksFlow.tsx
│           ├── MapView.tsx        ← Leaflet map + scan/sweep modes
│           ├── EvidenceCard.tsx   ← detection detail + YOLO verify
│           ├── YoloResultView.tsx ← SAR chip + bounding boxes
│           ├── DailyBriefing.tsx  ← Gemini executive briefing
│           ├── PatrolBoard.tsx    ← AI patrol ranking
│           ├── RiskTable.tsx      ← detections table + review
│           ├── AskOceanGuard.tsx  ← chat Q&A
│           ├── ModelMetrics.tsx   ← YOLO training stats
│           ├── DataSources.tsx    ← provenance reference
│           └── ResponsibleAIFooter.tsx
│
└── .github/
    └── workflows/                 ← GitHub Actions CI/CD → Cloud Run
```

---

## Live Data Feeds

| Feed | Status | Config key | What it provides |
|---|---|---|---|
| **GFW SAR** | ✅ Production | `GFW_API_TOKEN` | Dark-vessel SAR detections + AIS cross-match. Auto-loads at startup. |
| **AISStream** | ✅ Production | `AISSTREAM_API_KEY` | Live AIS to confirm dark detections via `POST /ais/verify-dark` |
| **WDPA MPAs** | ✅ Production | none (open ArcGIS) | MPA polygons for spatial risk scoring and map layer |
| **Sentinel-1 → YOLO** | ⚠️ Experimental | `SENTINELHUB_CLIENT_ID/SECRET` | On-demand SAR chip fetch for YOLO verify (domain gap, ~0.15 conf) |

See `LIVE_DATA.md` for full operational details.

---

## Risk Scoring Formula

```python
effective_conf = detection_conf * image_quality_score

ais_score = 0.3 if not ais_data_available else (0.0 if ais_matched else 1.0)
mpa_score = 1.0 if inside_mpa else (0.6 if near_mpa else 0.0)

risk = (0.30 * effective_conf +
        0.25 * ais_score +
        0.25 * mpa_score +
        0.10 * fishing_score +
        0.10 * repeated_activity_score)

# Thresholds
CRITICAL ≥ 0.75 | HIGH ≥ 0.55 | MEDIUM ≥ 0.35 | LOW < 0.35

# YOLO agreement boost (when YOLO confirms a GFW detection)
risk_score = min(0.99, risk_score + 0.10)
```

**Key thresholds:**
- AIS match: spatial ≤ 2 km + time window ± 3 hours
- Near MPA: ≤ 5 km from boundary
- Detection confidence: ≥ 0.45 to pass ingestion filter

---

## RiskEvent Schema

```jsonc
{
  "id": "bar-reef-003",
  "source": "GFW",                        // "GFW" or "YOLO_SAR"
  "lat": 8.51,
  "lon": 79.68,
  "risk_score": 0.61,
  "risk_level": "HIGH",
  "sar_confidence": 0.70,
  "image_quality": "Good",
  "ais_matched": false,
  "ais_data_available": true,
  "matching_method": "GFW server-side AIS cross-match",
  "inside_mpa": false,
  "near_mpa": true,
  "mpa_name": "Bar Reef Marine Sanctuary",
  "distance_to_mpa_km": 0.4,
  "distance_from_port_km": 33.1,
  "nearest_port": "Marina (OSM)",
  "timestamp": "2026-06-09T14:32:00Z",
  "review_status": "Pending",
  "why_flagged": "",                      // set by Gemini narrator
  "uncertainty": "",
  "confidence_threshold": 0.45,
  "recommended_action": "Human reviewer should verify scene and external context.",
  "thumbnail": null
}
```

---

## Backend API Routes

| Method | Path | Description |
|---|---|---|
| GET | `/health` | `{"status": "ok"}` |
| GET | `/risk-events` | All events; `?source=GFW|YOLO_SAR&level=HIGH&review_status=Pending` |
| GET | `/risk-events/{id}` | Single event or 404 |
| POST | `/risk-events/{id}/review` | Body: `{"review_status": "Confirmed Risk"}` |
| GET | `/mpa` | WDPA FeatureCollection |
| GET | `/mpa/status` | MPA count + source file |
| GET | `/ports` | ports.json |
| GET | `/model-metrics` | metrics.json |
| GET | `/ingest/status` | GFW feed config + events loaded |
| POST | `/ingest/gfw` | Manual GFW refresh |
| GET | `/ais/live` | Live AIS snapshot `?seconds=20` |
| POST | `/ais/verify-dark` | Confirm which detections have no nearby AIS |
| GET | `/verify/yolo/status` | `{"configured": true/false}` |
| POST | `/verify/yolo` | Point verify: `?lat=&lon=&date=&event_id=` |
| POST | `/verify/yolo/sweep` | Area sweep: `?min_lon=&min_lat=&max_lon=&max_lat=&date=` |
| POST | `/agents/narrate` | Body: RiskEvent → `{why_flagged, uncertainty}` |
| POST | `/agents/briefing` | Body: RiskEvent[] → situation summary |
| POST | `/agents/patrol` | Body: RiskEvent[] → ranked patrol list |
| POST | `/agents/ask` | Body: `{question: str}` → plain-English answer |

---

## AI Agent Layer (Gemini 2.5 Flash)

Model ID: `gemini-2.5-flash` — set in `backend/app/core/config.py`.

Auth: API key mode (`GEMINI_API_KEY`) or Vertex AI mode (`GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION`).

| Agent | Max tokens | Fallback |
|---|---|---|
| Narrator | 500 | Template string from event fields |
| Briefing | 600 | Template from highest-risk event |
| Patrol | 600 | Deterministic sort: inside_mpa → near_mpa → risk_score desc |
| Ask | 700 | "No AI available — check backend config." |

---

## Model Metrics (real values)

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
  "detections_on_real_scene": 122
}
```

---

## Environment Variables

### backend/.env
```
# Required for live AI agents
GEMINI_API_KEY=

# OR Vertex AI (Cloud Run production)
# GOOGLE_GENAI_USE_VERTEXAI=true
# GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_CLOUD_LOCATION=us-central1

# Live detection feed
GFW_API_TOKEN=
GFW_REGION_BBOX=-180.0,-90.0,180.0,90.0
GFW_LOOKBACK_DAYS=7
GFW_MAX_EVENTS=600
GFW_INGEST_ON_STARTUP=true

# Live AIS cross-check
AISSTREAM_API_KEY=

# On-demand YOLO verification (separate Cloud Run service)
YOLO_SERVICE_URL=

# Sentinel-1 chips for YOLO verify
SENTINELHUB_CLIENT_ID=
SENTINELHUB_CLIENT_SECRET=

CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### ml/.env (for live pipeline only)
```
SENTINELHUB_CLIENT_ID=
SENTINELHUB_CLIENT_SECRET=
GFW_REGION_BBOX=78.0,5.5,82.5,10.0
```

Secrets: **never commit**. Local = `.env` files. Production = GitHub Secrets → Cloud Run environment variables.

---

## Local Run

```bash
# 1. Copy and fill env files
cp backend/.env.example backend/.env
# fill GEMINI_API_KEY and GFW_API_TOKEN at minimum

# 2. Start everything
docker-compose up

# backend: http://localhost:8000
# frontend: http://localhost:5173
```

Dev without Docker:
```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

---

## Deploy (Production)

Push to `main` branch triggers GitHub Actions:
1. Builds Docker image for backend
2. Pushes to Google Artifact Registry
3. Deploys to Google Cloud Run

Frontend is also Cloud Run (nginx serving the Vite static build).

Credentials live in GitHub repository Secrets:
- `GFW_API_TOKEN`, `AISSTREAM_API_KEY`, `GEMINI_API_KEY`
- `SENTINELHUB_CLIENT_ID`, `SENTINELHUB_CLIENT_SECRET`
- `YOLO_SERVICE_URL`
- GCP service account for Cloud Run deployment

---

## Critical Demo Path

**Map → click bar-reef-003 (8.51°N 79.68°E, score 0.61 / HIGH, 0.4 km from MPA) → Evidence Card with Gemini explanation → Patrol Board ranks it #1.**

This single flow must always work. Everything else is supporting context.

---

## Tech Stack

| Layer | Choice |
|---|---|
| AI agents | Google Gemini 2.5 Flash (gemini-2.5-flash) via Google GenAI SDK |
| Detection model | YOLO11n (Ultralytics) — trained on HRSID, validated on xView3 |
| Geospatial | rasterio + pyproj + shapely (Shapely STRtree for MPA lookup) |
| Backend | FastAPI + Pydantic v2 + httpx |
| Live SAR | Global Fishing Watch API (primary) + Sentinel Hub/CDSE (on-demand) |
| Live AIS | AISStream.io WebSocket |
| MPA data | UNEP-WCMC WDPA open ArcGIS (no token) |
| Store | In-memory JSON (repository.py) |
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS |
| Map | react-leaflet (CartoDB DarkMatter, no API key) |
| Charts | recharts |
| Animations | Framer Motion |
| Icons | lucide-react |
| Deploy | Docker + GitHub Actions → Google Cloud Run + Artifact Registry |
