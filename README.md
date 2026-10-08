# OceanGuard AI

**Agent-driven dark-vessel detection inside Marine Protected Areas**

OceanGuard AI fuses Synthetic Aperture Radar (SAR) imagery, AIS vessel tracking, and spatial intelligence to identify and flag suspicious vessels operating inside MPAs without broadcasting their identity.

[![Deploy Backend](https://github.com/OceanguardAI/oceanguard/actions/workflows/deploy-backend.yml/badge.svg)](https://github.com/OceanguardAI/oceanguard/actions/workflows/deploy-backend.yml)
[![Deploy Frontend](https://github.com/OceanguardAI/oceanguard/actions/workflows/deploy-frontend.yml/badge.svg)](https://github.com/OceanguardAI/oceanguard/actions/workflows/deploy-frontend.yml)

---

## What it does

- **Live dark-vessel feed** — pulls Global Fishing Watch SAR detections (pinned to `public-global-sar-presence:v4.0`) and cross-references them against 10 800+ MPA polygons from the WDPA marine layer
- **On-demand SAR verification** — fetches a real Sentinel-1 chip from Copernicus CDSE for any selected vessel, runs it through a YOLO11n model, and shows the result on an evidence card
- **Area sweep** — tiles any user-drawn bounding box into up to 12 overlapping chips and runs YOLO on all of them in parallel
- **AI agents** — Gemini 2.5 Flash with tool-calling: Narrator (per-event explanation), Briefing (operational summary), Patrol (routing logic), Ask (free-form analyst queries over the detection database)
- **Risk scoring** — additive model combining GFW confidence, MPA proximity, and vessel type

---

## Architecture

```
Global Fishing Watch API (v4.0)
        │  SAR dark-vessel detections
        ▼
  FastAPI Backend  ←──────────────────────────────────┐
  backend/app/                                          │
  ├── services/gfw_ingest.py   (live fetch)             │
  ├── store/in_memory.py       (risk events)            │
  ├── agents/ask.py            (Gemini tool-calling)    │
  └── api/routes/verify.py     (SAR chip + YOLO)        │
        │                                               │
        │  REST API                                     │
        ▼                                               │
  React Dashboard (frontend/)                           │
        │  user clicks a vessel → verify                │
        ▼                                               │
  YOLO Service (yolo-service/)                          │
  ├── Sentinel Hub fetch (Sentinel-1 VV chip)           │
  └── YOLO11n inference → detections + base64 PNG ──────┘
```

**Data stores:** in-memory only (no PostgreSQL connected in current deployment). Seed data in `backend/data/risk_events.json`.

---

## ML Model

| Metric | Baseline (`best.pt`) | Fine-tuned (`finetuned_runE.pt`) |
|--------|---------------------|--------------------------------|
| Training data | HRSID (0.5–3 m SAR) | HRSID + xView3 Sentinel-1 |
| HRSID mAP@50 | 0.838 | 0.906 |
| xView3 overall recall | 30.9% | **42.2%** |
| 15–30 m vessel recall | 5% | **25%** |
| 30–60 m vessel recall | 9.5% | **43.7%** |
| ≥120 m vessel recall | 65.4% | 66.3% |
| FP / 100 km² | 0.37 | 0.92 |

`finetuned_runE.pt` was accepted after 4 Azure ML CPU training runs (B–E). Only Run E met both gates: xView3 recall increase **and** HRSID mAP drop ≤ 0.02 (actual drop: 0.007).

See [`ml/notebooks/training_runs_analysis.ipynb`](ml/notebooks/training_runs_analysis.ipynb) for full analysis, size-binned recall charts, and training curves.

---

## Project Structure

```
OceanEye/
├── backend/                  FastAPI service
│   ├── app/
│   │   ├── agents/           Gemini tool-calling agents (ask, narrator, briefing, patrol)
│   │   ├── api/routes/       REST endpoints
│   │   ├── services/         GFW ingest, Sentinel Hub
│   │   └── store/            In-memory + PostgreSQL (not connected) event stores
│   └── data/
│       ├── risk_events.json  Seed data (126 events)
│       └── metrics.json      Model performance numbers (authoritative)
│
├── frontend/                 React + Vite + Tailwind dashboard
│
├── yolo-service/             FastAPI microservice for YOLO inference
│   └── app/main.py           Sentinel chip fetch → YOLO11n → detections
│
├── ml/                       ML pipeline and training artifacts
│   ├── models/
│   │   ├── best.pt           HRSID baseline YOLO11n (mAP@50 = 0.838)
│   │   └── finetuned_runE.pt Accepted xView3 fine-tune (overall recall 42.2%)
│   ├── training/runs/        Azure ML run artifacts (B, C, D, E)
│   │   └── run_E/            Accepted run — summary, eval JSONs, results.csv
│   ├── datasets/labels/      xView3 label CSVs (train / val / subsets)
│   ├── notebooks/
│   │   └── training_runs_analysis.ipynb  Full fine-tuning analysis
│   ├── scripts/
│   │   ├── scene_selector.py
│   │   └── val_scene_selector.py
│   └── evaluation/
│       └── detection_by_size.py  Wilson-CI size-binned recall evaluator
│
├── docs/                     Reference documentation
│   ├── PROJECT_CONTEXT.md    ← start here for any new chat session
│   ├── SYSTEM_DEEP_DIVE.md   Full architecture, data flow, AI breakdown
│   ├── architecture.md
│   └── ...
│
└── scripts/
    └── azure_deploy.ps1      One-time Azure Container Apps provisioning
```

---

## Running Locally

### Prerequisites

- Python 3.11+, Node 18+
- API keys: `GFW_API_TOKEN`, `GEMINI_API_KEY`, `SENTINELHUB_CLIENT_ID`, `SENTINELHUB_CLIENT_SECRET`, `CARTO_API_KEY`

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
uvicorn app.main:app --reload --port 8000
```

### YOLO Service

```bash
cd yolo-service
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker (all services)

```bash
docker compose up --build
```

---

## Live Deployment

Runs on **Azure Container Apps** (`centralindia`):

| Service | Container App |
|---------|--------------|
| Backend API | `og-backend` |
| YOLO inference (scales to zero) | `og-yolo` |
| Frontend | `og-web` |

Push to `main` → GitHub Actions redeploys the changed service automatically.

**Secrets required in GitHub:** `AZURE_CREDENTIALS`, `GFW_API_TOKEN`, `GEMINI_API_KEY`, `SENTINELHUB_CLIENT_ID`, `SENTINELHUB_CLIENT_SECRET`, `CARTO_API_KEY`

**Variables required in GitHub:** `ACR_NAME`, `AZURE_RESOURCE_GROUP`, `VITE_API_BASE_URL`

---

## Data Sources

| Source | Used for | Notes |
|--------|----------|-------|
| [Global Fishing Watch API v3](https://globalfishingwatch.org/our-apis/) | SAR dark-vessel detections | Pinned to `v4.0`; `latest` flips to v5 on 21 Oct 2026 |
| [Copernicus CDSE](https://dataspace.copernicus.eu) | Sentinel-1 SAR chips | OAuth2 via `sentinelhub_client_id/secret` |
| [WDPA via ArcGIS](https://www.arcgis.com/home/item.html?id=2e5f2ec5e93f4c35b0e9da09e7cdb7f0) | MPA polygons (10 800+) | No token required |
| [xView3](https://iuu.xview.us) | Training / evaluation data | Account: `thanobansk@gmail.com` |

---

## Known Limitations

- **No live scoring:** scoring was removed from `gfw_ingest.py` (commit `8f07b9e`). Live GFW cells are unscored aggregates. Dashboard uses seed data.
- **Domain gap:** YOLO11n trained on HRSID (0.5–3 m pixels); live Sentinel-1 is 10 m pixels. Fine-tuned model (`finetuned_runE.pt`) closes part of this gap but is not yet wired to the live service.
- **No database:** `database_url=""` — all data is in-memory from seed JSON. `PostgresOperationalStore` exists but is not connected.
- **GFW v5 transition:** `public-global-sar-presence:latest` becomes v5 on 21 Oct 2026. Backend is pinned to `:v4.0` to prevent silent breakage.

---

## Research Questions

| ID | Question |
|----|----------|
| RQ1 | How does GFW v4 vs v5 detection coverage differ on identical time windows? |
| RQ2 | What is the minimum detectable vessel size at Sentinel-1 10 m resolution? |
| RQ3 | How does HRSID fine-tuning on xView3 affect recall across vessel size bins? |
| RQ4 | What preprocessing (chip overlap, CFAR, VH+VV) most improves small-vessel recall? |
| RQ5 | Can a tool-calling agent reliably abstract detection evidence without hallucinating? |

---

## Documentation

For a full architecture walkthrough, data flow trace, AI breakdown, and learning guide, read [`docs/SYSTEM_DEEP_DIVE.md`](docs/SYSTEM_DEEP_DIVE.md).

For current system state, honest live-data status, pending work list (P0–P3), and security gaps, read [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md).

---

## Azure ML

- **Subscription:** `901ad003-54c0-474f-bea8-cc3a36034d0c`
- **Workspace:** `oceanguard-ml` (centralindia)
- **Cluster:** `cpu-eval` (Standard_DS3_v2, 4 vCPU) — GPU quota is 0 on student sub
- **Completed runs:** B, C, D, E (all CPU, ~1 hr each)
- **Accepted run:** E — artifacts in `ml/training/runs/run_E/`
