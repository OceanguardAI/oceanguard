# OceanGuard AI — Full Technical Reference

> **Purpose:** Complete technical documentation — model training, datasets, APIs, architecture, data flow, limitations, and future roadmap. Written for engineers, ML practitioners, and technical reviewers.

---

## Table of Contents

1. [What the System Does](#1-what-the-system-does)
2. [Architecture Overview](#2-architecture-overview)
3. [Project Structure](#3-project-structure)
4. [Data Sources](#4-data-sources)
5. [ML Model — Training](#5-ml-model--training)
6. [ML Model — Inference Pipeline](#6-ml-model--inference-pipeline)
7. [Sentinel-1 SAR — How Images Are Fetched](#7-sentinel-1-sar--how-images-are-fetched)
8. [Risk Scoring Formula](#8-risk-scoring-formula)
9. [MPA Spatial Index](#9-mpa-spatial-index)
10. [Live Data Ingestion (GFW)](#10-live-data-ingestion-gfw)
11. [Backend Services & APIs](#11-backend-services--apis)
12. [AI Agents](#12-ai-agents)
13. [Frontend Architecture](#13-frontend-architecture)
14. [Infrastructure & Deployment](#14-infrastructure--deployment)
15. [Full Data Flow](#15-full-data-flow)
16. [Known Limitations](#16-known-limitations)
17. [Roadmap — What Would Make This Production-Grade](#17-roadmap--what-would-make-this-production-grade)

---

## 1. What the System Does

OceanGuard AI is a marine conservation decision-support tool that surfaces **dark vessels** — ships that have switched their AIS transponder off to avoid detection — near Marine Protected Areas (MPAs). It does this through two independent detection pipelines that are cross-referenced:

| Pipeline | Source | Method |
|---|---|---|
| **GFW layer** | Global Fishing Watch API | GFW runs their own SAR processing on Sentinel-1 imagery and cross-matches against AIS broadcasts server-side. We ingest their detections and apply our own risk scoring. |
| **YOLO layer** | Sentinel-1 via CDSE + our model | We fetch raw Sentinel-1 VV backscatter chips on demand and run our own fine-tuned YOLO11n model over them. This is entirely independent of GFW. |

When both pipelines agree on a contact, confidence is higher. When YOLO finds a contact that GFW did not report, it is a **new dark-vessel candidate** for patrol.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        OFFICER'S BROWSER                         │
│   React + Leaflet + Framer Motion (oceanguard-web Cloud Run)     │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTPS REST
┌────────────────────────────▼─────────────────────────────────────┐
│                    BACKEND API                                   │
│   FastAPI (oceanguard-api Cloud Run)                             │
│   • In-memory RiskEvent store (600 events, refreshed ~30s)       │
│   • GFW ingest thread (startup, then on-demand)                  │
│   • Sentinel Hub SAR chip proxy                                  │
│   • YOLO verify + area sweep proxy                               │
│   • AI agents (Gemini via Vertex AI)                             │
│   • MPA spatial index (WDPA GeoJSON, shapely STRtree)            │
└──────┬────────────────────────────────┬────────────────────────────┘
       │ REST (GFW API token)            │ REST (CDSE OAuth + httpx)
       ▼                                 ▼
┌──────────────┐              ┌──────────────────────────────────┐
│  GFW API     │              │       YOLO SERVICE               │
│  global SAR  │              │  oceanguard-yolo Cloud Run       │
│  detections  │              │  FastAPI + torch==2.5.1 (CPU)    │
│  (600 events │              │  + ultralytics YOLO11n           │
│   per ingest)│              │  + Sentinel Hub Process API      │
└──────────────┘              └──────────────────────────────────┘
                                         │ CDSE OAuth
                                         ▼
                              ┌──────────────────────────────────┐
                              │  Sentinel Hub Process API (CDSE) │
                              │  Sentinel-1 GRD VV backscatter   │
                              │  640×640px chips, IW mode        │
                              └──────────────────────────────────┘
```

Three separate Cloud Run services so concerns are fully isolated:
- `oceanguard-web` — static React frontend
- `oceanguard-api` — Python backend (1Gi/1CPU, no-CPU-throttling)
- `oceanguard-yolo` — torch inference service (2Gi/2CPU, scale-to-zero)

---

## 3. Project Structure

```
OceanEye/
│
├── frontend/                    React + TypeScript SPA
│   ├── src/
│   │   ├── App.tsx              Root: state, layout, scan/sweep wiring
│   │   ├── components/
│   │   │   ├── MapView.tsx      Leaflet map, MPA polygons, event markers,
│   │   │   │                    scan crosshair, sweep rectangle + contacts
│   │   │   ├── EvidenceCard.tsx Detection detail: SAR chip, YOLO confirm button
│   │   │   ├── YoloResultView.tsx Shared YOLO result: chip + bounding boxes
│   │   │   ├── PatrolBoard.tsx  Top-3 patrol targets (AI-ranked)
│   │   │   ├── DailyBriefing.tsx Morning situation report
│   │   │   ├── AskOceanGuard.tsx Chat agent (Gemini tool-calling)
│   │   │   └── RiskTable.tsx    Scrollable detection queue
│   │   ├── lib/
│   │   │   └── api.ts           All fetch calls to the backend
│   │   └── types/index.ts       RiskEvent, SweepResult, etc.
│   └── vite.config.ts
│
├── backend/                     FastAPI Python API
│   ├── app/
│   │   ├── core/config.py       All settings via pydantic-settings
│   │   ├── models/schemas.py    Pydantic models (RiskEvent, PatrolItem…)
│   │   ├── store/repository.py  In-memory event store + filters
│   │   ├── services/
│   │   │   ├── gfw_ingest.py    GFW API → RiskEvent conversion + scoring
│   │   │   ├── sentinel_sar.py  Sentinel Hub SAR chip fetcher (display)
│   │   │   ├── ais_stream.py    AISStream.io WebSocket sampler
│   │   │   └── mpa_index.py     Shapely STRtree MPA spatial index
│   │   ├── api/routes/
│   │   │   ├── events.py        GET /risk-events, PATCH /review
│   │   │   ├── sar.py           GET /sar-image (display chip)
│   │   │   ├── verify.py        POST /verify/yolo, POST /verify/yolo/sweep
│   │   │   ├── geo.py           GET /mpa (viewport-clipped WDPA polygons)
│   │   │   ├── agents.py        POST /agents/narrate|briefing|patrol|ask
│   │   │   └── metrics.py       GET /model-metrics
│   │   └── agents/
│   │       ├── ask.py           Gemini tool-calling Q&A agent
│   │       ├── briefing.py      Daily situation summary agent
│   │       ├── patrol.py        Patrol prioritisation agent
│   │       └── narrator.py      Per-detection explanation agent
│   └── data/
│       ├── mpas.geojson         Global WDPA marine protected areas
│       ├── bar_reef.geojson     Fallback single MPA (Sri Lanka)
│       ├── ports.json           Port locations for distance scoring
│       ├── metrics.json         Trained model metrics (served to UI)
│       └── risk_events.json     Offline fallback seed events
│
├── yolo-service/                Torch inference microservice
│   ├── app/
│   │   ├── main.py              FastAPI: /health, /detect-point
│   │   ├── config.py            Settings: CDSE URLs, chip geometry, threshold
│   │   ├── sentinel.py          Sentinel Hub chip fetcher (YOLO-sized)
│   │   └── inference.py         YOLO11n model runner + pixel→lat/lon
│   ├── models/best.pt           Fine-tuned YOLO11n (5.5MB, 1 class: ship)
│   ├── Dockerfile               python:3.11-slim + torch==2.5.1 CPU
│   └── .dockerignore            Excludes __pycache__, .pyc from build
│
├── ml/                          Training + offline ML pipeline
│   ├── pipeline/
│   │   ├── tiling.py            GeoTIFF → 640×640 tile PNGs
│   │   ├── detect.py            YOLO11n inference on tiles
│   │   ├── georeference.py      Pixel → UTM → lat/lon (EPSG:32631→4326)
│   │   ├── enrich.py            MPA distance, port distance
│   │   └── risk.py              Risk score + level formula
│   ├── models/best.pt           Same weights shipped to yolo-service
│   ├── outputs/
│   │   ├── detections_scene1_georef.json  122 cached YOLO detections
│   │   └── risk_events.json     126-event output of the offline pipeline
│   ├── run_full_ml_workflow.py  Main entry point (5-stage pipeline)
│   └── requirements.txt         ultralytics, rasterio, pyproj, shapely
│
└── .github/workflows/
    ├── deploy-backend.yml       Push to main → build + deploy oceanguard-api
    ├── deploy-yolo.yml          Push to main → build + deploy oceanguard-yolo
    └── deploy-frontend.yml      Push to main → build + deploy oceanguard-web
```

**Why three services instead of one?**

| Reason | Detail |
|---|---|
| torch is 800MB+ | Putting torch in the API container would slow every backend deploy and bloat the image. The YOLO service only starts when an officer actually runs a scan. |
| Scale-to-zero | The YOLO service costs nothing between scans. The backend stays warm (no cold starts on officer load). |
| Independent failure | A YOLO crash does not affect the live detection feed or the AI agents. |

---

## 4. Data Sources

### 4.1 Global Fishing Watch (GFW) API
- **Endpoint:** `https://gateway.api.globalfishingwatch.org/v3/4wings/report`
- **Dataset:** `public-global-sar-presence:latest`
- **Auth:** Bearer token (`GFW_API_TOKEN` GitHub Secret)
- **What we fetch:** SAR vessel detections for the last 7 days across `[-180,-90,180,90]` (global). Each entry has lat/lon, detection count, timestamp, and optionally vesselId/MMSI/shipName if GFW matched it to AIS.
- **Volume:** ~10,000–50,000 raw detections globally per 7-day window. We de-duplicate by 0.5° cells and stratified-sample down to 600 events (15% CRITICAL, 30% HIGH, 35% MEDIUM, 20% LOW).
- **Dark vessel signal:** An entry with no vesselId/MMSI = GFW's SAR processor saw a vessel but found no AIS match. This is the core "dark vessel" signal.

### 4.2 Sentinel-1 GRD (via Sentinel Hub / CDSE)
- **Provider:** Copernicus Data Space Ecosystem (CDSE) — free tier
- **Auth:** OAuth2 client credentials (`SENTINELHUB_CLIENT_ID/SECRET` GitHub Secrets)
- **Token URL:** `https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token`
- **Process API:** `https://sh.dataspace.copernicus.eu/api/v1/process`
- **Satellite:** Sentinel-1A/B, C-band SAR (5.4 GHz), Interferometric Wide (IW) mode
- **Polarisation:** VV (vertical transmit, vertical receive)
- **Why VV?** Ships are vertical metal structures — VV polarisation gives stronger returns from vertical edges = brighter ship signatures.
- **Revisit time:** ~6–12 days per location (two satellites, inclined orbits)
- **Display chip:** 384×384px, ±0.05° (~11km across), used in EvidenceCard
- **YOLO chip:** 640×640px, ±0.02° (~4.4km across), used for inference. Tighter window = ships appear larger relative to the image = better detection.
- **Evalscript:** `Math.max(0, Math.min(1, 2.5 * s.VV))` — linear stretch of VV backscatter to 8-bit. Ships (bright) and water (dark) are clearly separated.

### 4.3 HRSID (Training Dataset)
- **Full name:** High-Resolution SAR Images Dataset
- **Size:** 5604 images (2857 train / 715 val / 1032 test after our 80/20 split)
- **Annotations:** Ship bounding boxes in YOLO format, single class ("ship")
- **SAR sensors:** Sentinel-1, Gaofen-3, TerraSAR-X at multiple resolutions (3m, 1m)
- **Why HRSID:** Freely available, widely used benchmark for SAR ship detection. Covers diverse sea states, incidence angles, and ship sizes.
- **Limitation:** See Section 16.

### 4.4 xView3 (Validation Scene)
- **Scene ID:** `590dd08f71056cacv`
- **Location:** Gulf of Guinea, West Africa
- **Size:** 28,676 × 24,522 pixels at 10m/pixel (~287 × 245 km coverage)
- **Used for:** Offline validation — we tiled this scene and ran our trained model over it to produce 122 detections, proving the model works on a real independent scene outside HRSID.

### 4.5 WDPA Marine Protected Areas
- **Source:** World Database on Protected Areas (WDPA) via ArcGIS open API
- **Coverage:** Global, ~10,000 marine polygons loaded at startup
- **Format:** GeoJSON FeatureCollection stored as `backend/data/mpas.geojson`
- **Use:** Every detection's `distance_to_mpa_km`, `inside_mpa`, `near_mpa`, `mpa_name` comes from querying this index.

### 4.6 AISStream.io
- **Purpose:** Cross-reference YOLO detections against live AIS broadcasts
- **Method:** Short WebSocket sampling window (~20s) over the monitored bbox
- **Dark vessel signal:** `confirms_dark()` — a SAR contact with no AIS vessel within 2km is a confirmed dark signal.
- **Status:** Integrated but not fully surfaced in the UI yet; primarily used in backend scoring logic.

### 4.7 Ports (OSM-derived)
- **File:** `backend/data/ports.json`
- **Use:** Haversine distance from detection to nearest port, shown in EvidenceCard. Contextual — a dark vessel near a port is different from one far offshore.

---

## 5. ML Model — Training

### 5.1 Model Architecture
- **Base:** YOLOv11n (nano variant) — the smallest YOLO11 model
- **Task:** Single-class object detection (class 0 = "ship")
- **Weights file:** `best.pt`, 5.5MB
- **Framework:** Ultralytics ≥8.0.0

### 5.2 Why YOLO11n?
- **Nano is intentional:** SAR ship detection does not need a large backbone. Ships are distinct bright blobs on dark water — a small model generalises well and runs in ~200ms on CPU per 640×640 chip.
- **CPU inference only:** The YOLO service runs on Cloud Run with 2 vCPU, no GPU. YOLO11n is fast enough (no GPU available).
- **No GPU during training:** Training was done on Google Colab free tier (T4 GPU, 50 epochs, ~40 minutes).

### 5.3 Training Configuration

| Parameter | Value |
|---|---|
| Dataset | HRSID (pre-converted to YOLO format) |
| Train split | 2857 images |
| Val split | 715 images |
| Image size | 640×640 (native YOLO input) |
| Epochs | 50 |
| Batch size | 16 |
| Optimizer | SGD (Ultralytics default) |
| Augmentation | Mosaic, random flip, HSV jitter (Ultralytics defaults) |
| Confidence threshold (training) | 0.45 |
| Confidence threshold (inference) | 0.25 (lowered post-training to increase recall) |

### 5.4 Training Results

| Metric | Value |
|---|---|
| mAP@50 | **0.838** |
| mAP@50-95 | 0.579 |
| Precision | 0.830 |
| Recall | 0.818 |

Training curve (mAP50 by epoch):
```
Epoch  1:  0.61  (loss 1.80)
Epoch 10:  0.72  (loss 1.20)
Epoch 20:  0.78  (loss 0.90)
Epoch 30:  0.81  (loss 0.70)
Epoch 40:  0.83  (loss 0.60)
Epoch 50:  0.838 (loss 0.55)
```

Model converged cleanly with no sign of overfitting at epoch 50. The loss curve shows diminishing returns after epoch 40 — more epochs would not significantly improve mAP.

### 5.5 Fine-Tuning Details
We started from **pretrained YOLO11n COCO weights** (not random init) and fine-tuned on HRSID. This is transfer learning — the backbone's feature extraction already understands shapes and edges; we only needed to teach the head what SAR ship returns look like.

Why fine-tune vs. train from scratch:
- HRSID has ~3,500 train images — not enough for a clean random-init training
- Pretrained backbone converges 3–5× faster and reaches higher mAP on small datasets
- SAR images look visually different from optical RGB (COCO), but low-level features (edges, blobs, gradients) transfer well

---

## 6. ML Model — Inference Pipeline

### 6.1 Offline Pipeline (training → risk_events.json)

Used once to produce the seed data file. The five stages:

```
GeoTIFF (700MB)
    │
    ▼ tiling.py
640×640 tiles (1174 valid tiles from 28676×24522 scene)
    │   — windowed rasterio reads (never loads full GeoTIFF)
    │   — skips tiles with <50% valid pixels
    ▼ detect.py
Raw detections (122 ships found at conf ≥0.45)
    │   — JSON checkpointing every 25 tiles
    ▼ georeference.py
lat/lon coordinates
    │   — UTM pixel → EPSG:32631 → EPSG:4326 via pyproj
    │   — 10m/pixel ground sample distance from scene metadata
    ▼ enrich.py
+ MPA distance, inside_mpa, near_mpa
+ nearest port distance
    ▼ risk.py
risk_score (0.0–0.99), risk_level (LOW/MEDIUM/HIGH/CRITICAL)
    │
    ▼
risk_events.json (126 events: 122 YOLO_SAR + 4 GFW)
```

### 6.2 Live Inference (on-demand per officer click)

```
Officer clicks "Run YOLO check" or "Sweep area"
    │
    ▼ Backend /verify/yolo or /verify/yolo/sweep
POST to oceanguard-yolo /detect-point {lat, lon, date}
    │
    ▼ sentinel.py (yolo-service)
POST Sentinel Hub Process API
    → bearer token from CDSE OAuth (cached 30min)
    → sentinel-1-grd, IW mode, DV polarisation
    → timeRange: [date-12d, date+1d]  (12-day search window)
    → bbox: [lon±0.02, lat±0.02]
    → output: 640×640 PNG, VV evalscript
    → returns raw PNG bytes
    │
    ▼ inference.py
PIL.Image.open → np.array → YOLO11n.predict()
    → conf_threshold=0.25
    → device="cpu"
    → returns boxes: [x1,y1,x2,y2, confidence]
    │
    ▼ pixel → lat/lon
linear interpolation across chip bbox
    │
    ▼ response
{found, count, best_confidence, detections[], chip_png_b64, chip_bbox}
```

### 6.3 Area Sweep

For "Sweep area", the backend tiles the viewport into 0.04°×0.04° chips (capped at 12 tiles) and runs detect-point on each in parallel (4 workers). Each contact is cross-referenced against the live GFW store:
- **Contact within 2km of a known GFW detection** → `confirmed`
- **No nearby GFW detection** → `new` (dark vessel candidate for patrol)

---

## 7. Sentinel-1 SAR — How Images Are Fetched

The same CDSE credentials serve two different chip sizes for two different purposes:

| | Display chip (EvidenceCard) | YOLO chip (inference) |
|---|---|---|
| **File** | `sentinel_sar.py` (backend) | `sentinel.py` (yolo-service) |
| **Size** | 384×384px | 640×640px |
| **Half-width** | ±0.05° (~11km) | ±0.02° (~4.4km) |
| **Resolution** | ~29m/px | ~7m/px |
| **Why different** | Human visual context needs wider view | YOLO needs ships to appear ~10px wide (matches HRSID training resolution) |
| **Evalscript** | `2.5 * s.VV` clamp 0-1 | Same evalscript |
| **Search window** | Last 12 days from event timestamp | Last 12 days from supplied date |

**Why 12 days?** Sentinel-1 revisit period is 6–12 days depending on latitude and which satellite is in the constellation. A 12-day window guarantees at least one pass is available almost anywhere on Earth.

---

## 8. Risk Scoring Formula

Two slightly different formulas exist — the offline ML pipeline and the live GFW ingest. Both implement the same logic; the live version uses live MPA proximity data.

### Live formula (gfw_ingest.py)

```python
score = 0.25  # baseline: any SAR detection
if not ais_matched:
    score += 0.20  # dark vessel (no AIS identity)
if distance_to_mpa_km <= 0:
    score += 0.45  # inside the protected area
elif distance_to_mpa_km <= 10:
    score += 0.30  # near the boundary
elif distance_to_mpa_km <= 50:
    score += 0.15  # surrounding waters
if detections > 1:
    score += 0.05  # repeated presence at this cell
score = min(score, 0.99)

# Thresholds:
CRITICAL: score >= 0.80
HIGH:     score >= 0.60
MEDIUM:   score >= 0.45
LOW:      otherwise
```

**Example — vessel inside MPA, dark:**
`0.25 + 0.20 + 0.45 = 0.90 → CRITICAL`

**Example — vessel 20km from MPA, AIS present:**
`0.25 + 0.00 + 0.15 = 0.40 → LOW`

### YOLO agreement boost
When our model confirms the same point as a GFW detection, the risk score is raised by `+0.10` (capped at 0.99) and the `matching_method` is annotated with `YOLO-confirmed (Sentinel-1)`. This is in-memory only — the seed file is not modified.

---

## 9. MPA Spatial Index

- **Implementation:** `shapely.STRtree` (Sort-Tile-Recursive tree) over ~10,000 WDPA polygons
- **Lookup complexity:** O(log n) per point — can score tens of thousands of GFW detections at startup without noticeable delay
- **Thread safety:** Built atomically behind a lock; concurrent ingest + API requests see either the old or new complete index, never a half-built one
- **Containment check:** `STRtree.query(point, predicate="intersects")` — returns all polygons the point falls inside
- **Distance check:** `STRtree.query_nearest(point)` → `nearest_points(point, polygon)` → `haversine_km` for true great-circle distance
- **Near MPA threshold:** 10km (`NEAR_MPA_KM`)
- **Fallback:** If `mpas.geojson` is missing, falls back to `bar_reef.geojson` (single Sri Lanka polygon)
- **Viewport clipping:** `features_in_bbox()` returns only MPAs in the map's current viewport, so the frontend never loads the full global set at once

---

## 10. Live Data Ingestion (GFW)

### Startup sequence
```
Cloud Run container starts
    │
    ├─ MPA index loads (mpas.geojson → STRtree, ~1s)
    ├─ Ports load (ports.json → list)
    ├─ Seed events load (risk_events.json → in-memory store)
    │   └─ API is ready to serve (health passes)
    │
    └─ Background thread (if GFW_INGEST_ON_STARTUP=true)
           ├─ GFW API call (~10-30s for global query)
           ├─ Score each detection (MPA proximity, AIS match)
           ├─ De-duplicate by 0.5° cell
           ├─ Stratified sample → 600 events
           └─ Replaces in-memory store (~30s after cold start)
```

### De-duplication and sampling
Global SAR coverage returns ~10,000–50,000 raw detections. Processing steps:
1. **Sort by risk score** (highest first)
2. **De-duplicate:** Keep only the highest-scoring detection per 0.5° cell (~55km grid)
3. **Stratified sample** to 600 events: 15% CRITICAL, 30% HIGH, 35% MEDIUM, 20% LOW — ensures the map shows a realistic risk pyramid, not 600 CRITICAL markers

The 30-second poll on the frontend picks up the updated store automatically.

---

## 11. Backend Services & APIs

### Key endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/risk-events` | All events; optional `?source=GFW&level=CRITICAL` filters |
| POST | `/risk-events/{id}/review` | Update review status (Pending/Confirmed Risk/False Positive/Resolved) |
| GET | `/sar-image` | Sentinel-1 display chip PNG for a lat/lon/date |
| GET | `/sar-image/status` | Whether CDSE credentials are configured |
| POST | `/verify/yolo` | Single-point YOLO check — `?lat=&lon=&date=&event_id=` |
| POST | `/verify/yolo/sweep` | Area sweep — `?min_lon=&min_lat=&max_lon=&max_lat=&date=` |
| GET | `/verify/yolo/status` | Whether YOLO service URL is configured |
| GET | `/mpa` | WDPA polygons for a viewport bbox |
| GET | `/model-metrics` | Trained model metrics (served to ML Validation tab) |
| POST | `/agents/narrate` | Per-event AI explanation (Gemini) |
| POST | `/agents/briefing` | Daily situation summary (Gemini) |
| POST | `/agents/patrol` | Patrol priority ranking (Gemini) |
| POST | `/agents/ask` | Free-text Q&A with tool-calling (Gemini) |

### In-memory store
`repository.py` holds all events in a `dict[str, RiskEvent]`. No database. Deliberate choice — a Cloud Run instance lives ~hours at most; the store is rebuilt from GFW on each cold start. Filters (`source`, `level`, `review_status`, `near_mpa`) are pure Python list comprehensions.

---

## 12. AI Agents

All agents use **Gemini 2.5 Flash via Vertex AI** (`gemini-2.5-flash`). Every agent has a deterministic Python fallback that runs when Gemini is unavailable, so the UI always gets a response.

### Narrator
- **Input:** Single `RiskEvent`
- **Output:** `why_flagged` and `uncertainty` — human-readable explanation of why this detection was flagged
- **Token budget:** 500 tokens

### Briefing
- **Input:** Up to 10 top events + summary statistics
- **Output:** 2–4 sentence plain-prose situation report
- **Token budget:** 400 tokens
- **Use:** Morning shift summary

### Patrol
- **Input:** Up to 20 events
- **Output:** JSON array of `PatrolItem` ranked by patrol priority
- **Ranking logic:** risk_score → inside_mpa → near_mpa → distance_to_mpa_km
- **Token budget:** 600 tokens
- **Use:** Which vessel to dispatch a patrol boat to first

### Ask (Q&A Agent)
- **Architecture:** Tool-calling loop (up to 5 rounds)
- **System prompt:** Injects the **complete live dataset** (~13k tokens at 600 events) so Gemini can answer any question about current detections without needing tool calls for simple queries
- **Tools:** `query_detections` (filter by level/source/near_mpa), `get_event`, `get_risk_summary`, `get_model_metrics`, `get_ports`
- **Token budget:** 700 tokens
- **Example questions:** "Give all ships near MPA", "Which vessel is highest risk?", "How many dark vessels in the last week?"

---

## 13. Frontend Architecture

- **Framework:** React 18 + TypeScript + Vite
- **Map:** Leaflet via `react-leaflet` — CartoDB dark tiles basemap
- **Animations:** Framer Motion (AnimatePresence for panel transitions)
- **State:** All in `App.tsx` — no Redux/Zustand. State is: events, selectedEvent, leftPanel, scanMode, scanPoint, sweepBbox, sweepResult, assistantOpen, etc.
- **Polling:** `setInterval` every 30 seconds re-fetches events; selected event is preserved across polls

### Map layers (bottom to top)
1. CartoDB dark basemap tiles
2. WDPA MPA polygons (dashed teal, viewport-clipped)
3. GFW detection markers (coloured dots by risk level)
4. Sweep rectangle (cyan dashed outline of scanned area)
5. YOLO sweep contacts (red diamond = new, teal diamond = confirmed)
6. Scan point crosshair (pulsing cyan)

### Right panel priority
When multiple things compete for the right panel:
`sweep active` > `assistant open` > `evidence card`

---

## 14. Infrastructure & Deployment

### Cloud Run services

| Service | CPU | Memory | Min instances | Max instances | Scale to zero |
|---|---|---|---|---|---|
| oceanguard-web | 1 | 512Mi | 0 | 3 | Yes |
| oceanguard-api | 1 | 1Gi | 0 | 3 | Yes (no-CPU-throttling on) |
| oceanguard-yolo | 2 | 2Gi | 0 | 3 | Yes |

`--no-cpu-throttling` on the API keeps the background ingest thread running at full speed; without it, Cloud Run would throttle the CPU to near-zero after the request completes, stalling the GFW ingest.

### CI/CD

Every push to `main` triggers the relevant workflow:
- Changes to `backend/**` → `deploy-backend.yml`
- Changes to `yolo-service/**` → `deploy-yolo.yml`
- Changes to `frontend/**` → `deploy-frontend.yml`
- `workflow_dispatch` on each workflow for credential-only redeploys (no code change needed)

### Secrets management

| Secret | Stored in | Injected via |
|---|---|---|
| `GFW_API_TOKEN` | GitHub Secrets | Cloud Run env (workflow writes `cloudrun-env.yaml`) |
| `SENTINELHUB_CLIENT_ID` | GitHub Secrets | Cloud Run env (both backend + yolo workflows) |
| `SENTINELHUB_CLIENT_SECRET` | GitHub Secrets | Cloud Run env (both) |
| `AISSTREAM_API_KEY` | GitHub Secrets | Cloud Run env (backend) |
| `GEMINI_*` | GitHub Vars + Workload Identity | Vertex AI (no API key needed — service account auth) |

Updating a GitHub Secret does **not** redeploy. You must trigger `workflow_dispatch` on the affected workflow after updating secrets.

### Authentication to GCP
Workload Identity Federation — no long-lived service account key files anywhere. GitHub Actions authenticates to GCP using short-lived OIDC tokens.

---

## 15. Full Data Flow

### Officer loads the dashboard
```
Browser → GET /risk-events
Backend → loads seed events from risk_events.json (instant)
            └─ Background: GFW API call → score → update store (~30s)
Browser polls every 30s → picks up live data
```

### Officer clicks a detection
```
Browser → selects event from map/list
          → EvidenceCard shows: risk score, AIS status, MPA proximity,
            recommended action, AI narrator explanation
          → GET /sar-image → 384px Sentinel-1 chip displayed
```

### Officer clicks "Run YOLO check"
```
Browser → POST /verify/yolo?lat=&lon=&date=&event_id=
Backend → POST oceanguard-yolo /detect-point {lat, lon, date}
YOLO service:
  → CDSE OAuth token (cached)
  → POST Sentinel Hub: 640×640 chip
  → YOLO11n.predict() on chip
  → pixel coords → lat/lon
  → returns {found, count, detections[], chip_png_b64}
Backend:
  → if found AND event exists in store: +0.10 risk boost, annotate
  → returns result to browser
Browser → draws bounding boxes on chip image (SVG overlay)
```

### Officer clicks "Sweep area"
```
Browser → POST /verify/yolo/sweep?min_lon=&min_lat=&max_lon=&max_lat=&date=
Backend:
  → tiles area into 0.04°×0.04° chips (max 12)
  → ThreadPoolExecutor(workers=4): POST each to YOLO service
  → cross-reference each YOLO contact against live store
    (within 2km of known event → "confirmed", else → "new")
  → returns {tiles_scanned, new_contacts, confirmed_contacts, contacts[]}
Browser:
  → draws sweep rectangle on map
  → red diamond markers = new (dark vessel candidates)
  → teal diamond markers = confirmed
```

---

## 16. Known Limitations

### 16.1 Small Training Dataset
**HRSID has 3,572 train+val images.** This is small for a production detection model. Typical production SAR ship detectors (SARDet-100K, xView3) use 100,000+ images. Consequences:

- Model may not generalise well to:
  - Very large vessels (supertankers, carriers) — underrepresented in HRSID
  - Unusual SAR incidence angles (HRSID is mostly mid-range angles)
  - High sea states (wave clutter can cause false positives)
  - Polar/arctic conditions (different backscatter characteristics)
- mAP50=0.838 on HRSID validation is good but on a small held-out set — real-world performance is likely lower

**Mitigation path:** Fine-tune on SAR-Ship-1000 + SARDet-100K + xView3 annotated scenes. This would likely push mAP50 to 0.92+ and dramatically improve recall on small targets.

### 16.2 Single Class — No Vessel Type Classification
The model outputs one class: "ship". It cannot distinguish:
- Fishing vessel vs cargo vs tanker vs military
- Moving vs stationary vessel
- Size (length estimate is possible from bounding box but not implemented)

**Why:** HRSID annotations are single-class. Multi-class SAR ship classification requires a separate, harder dataset (e.g., FUSAR-Ship with 15 vessel categories).

### 16.3 Sentinel-1 Revisit Gap
**6–12 day revisit.** An officer clicking "Run YOLO check" on a vessel seen 7 days ago by GFW will often see empty water — the vessel has moved. The 12-day search window mitigates this but does not solve it.

Sentinel-1C (launched 2024) is improving revisit to ~3–4 days. Higher-revisit commercial SAR (ICEYE, Capella, Umbra) provides near-daily coverage but requires commercial access.

### 16.4 Confidence Threshold Tuning
`conf_threshold=0.25` was chosen empirically. At this setting:
- Small boats (15–30m) may score below threshold and be missed
- In high-clutter scenes (rough sea, coastal areas) there will be false positives (sea speckle misclassified as ship)

This is a classic precision-recall tradeoff. The threshold is an env var (`CONF_THRESHOLD`) so it can be adjusted without code change.

### 16.5 No Historical Tracking
Each detection is a snapshot. We do not:
- Track the same vessel across multiple SAR passes
- Compute vessel trajectories
- Detect vessels that stop transmitting mid-voyage

GFW's commercial API has vessel track data that could address this.

### 16.6 Area Sweep Cap
The sweep is capped at **12 tiles** to bound cost and latency. A 12-tile sweep takes ~2–3 minutes (YOLO service cold start included). A full MPA the size of the Great Barrier Reef (~344,000 km²) would require thousands of tiles — not feasible with the current per-request model.

**Mitigation:** Batch processing — schedule a nightly sweep of all active MPAs, store results, serve pre-computed heat maps. This is architecturally straightforward but not yet implemented.

### 16.7 In-Memory Store — No Persistence
The backend stores all events in memory. A Cloud Run instance restart (happens frequently on scale-to-zero) drops all officer review annotations. There is no database.

**Mitigation:** Firestore or Cloud SQL for persistence of review decisions.

### 16.8 GFW Data Latency
GFW SAR detections are typically **6–12 hours to several days old** by the time they appear in the API. This is not a bug — SAR satellite tasking, downlink, and GFW processing all take time. OceanGuard is a decision-support tool for patrol planning, not real-time interception.

---

## 17. Roadmap — What Would Make This Production-Grade

### Short-term (weeks)

| Item | What | Why |
|---|---|---|
| Larger training dataset | Fine-tune on SAR-Ship-1000 + SARDet-100K | mAP50 → ~0.92, better small-boat recall |
| Persist review decisions | Add Firestore for officer annotations | Survive instance restarts |
| Scheduled MPA sweep | Nightly batch sweep of all active MPAs | Remove 12-tile cap, async results |
| Vessel size estimate | Bounding box → estimated vessel length | Fishing boat vs cargo is operationally important |

### Medium-term (months)

| Item | What | Why |
|---|---|---|
| Multi-class detection | Vessel type classification model | Distinguish fishing, cargo, tanker |
| Track linking | Associate detections across SAR passes | Detect vessels that stop transmitting mid-voyage |
| ICEYE/Capella integration | Near-daily SAR via commercial API | Solve the 6-12 day revisit gap |
| AIS gap analysis | Flag vessels that were transmitting and then stopped | Strong enforcement signal |
| Mobile officer app | React Native version of the dashboard | Field use on patrol boats |

### Long-term (production)

| Item | What | Why |
|---|---|---|
| GPU inference | Cloud Run with GPU, or Cloud Batch | 10× faster sweeps, larger areas |
| Full WDPA sweep | Nightly scan of all ~10,000 MPAs | Proactive global surveillance |
| Confidence calibration | Platt scaling on YOLO outputs | Well-calibrated probabilities for risk formulas |
| Human-in-the-loop retraining | Officer "false positive" labels → RLHF loop | Model improves from operational use |
| Integration with enforcement systems | API handoff to maritime patrol agencies | Close the loop from detection to action |

---

## Appendix A — Environment Variables

| Variable | Service | Description |
|---|---|---|
| `GFW_API_TOKEN` | backend | Global Fishing Watch API bearer token |
| `SENTINELHUB_CLIENT_ID` | backend + yolo | CDSE OAuth client ID |
| `SENTINELHUB_CLIENT_SECRET` | backend + yolo | CDSE OAuth client secret |
| `SENTINELHUB_TOKEN_URL` | backend + yolo | CDSE token endpoint (pinned in workflow) |
| `SENTINELHUB_PROCESS_URL` | backend + yolo | CDSE process API endpoint (pinned in workflow) |
| `YOLO_SERVICE_URL` | backend | URL of oceanguard-yolo Cloud Run service |
| `AISSTREAM_API_KEY` | backend | AISStream.io WebSocket API key |
| `GEMINI_MODEL` | backend | Gemini model ID (`gemini-2.5-flash`) |
| `GOOGLE_CLOUD_PROJECT` | backend | GCP project for Vertex AI |
| `GFW_MAX_EVENTS` | backend | Max events to keep after stratified sampling (600) |
| `GFW_LOOKBACK_DAYS` | backend | Days back for GFW SAR query (7) |
| `CONF_THRESHOLD` | yolo | YOLO inference confidence threshold (0.25) |

## Appendix B — Third-Party Libraries

| Library | Version | Purpose |
|---|---|---|
| `ultralytics` | ≥8.0.0 | YOLO11n model training and inference |
| `torch` | ==2.5.1 (pinned) | PyTorch CPU inference runtime |
| `torchvision` | ==0.20.1 (pinned) | Matched torchvision (NMS ops) |
| `fastapi` | ≥0.110.0 | API framework (backend + yolo) |
| `pydantic-settings` | ≥2.0.0 | Settings management from env vars |
| `httpx` | ≥0.27.0 | Async-capable HTTP client (Sentinel Hub, GFW) |
| `shapely` | ≥2.0.0 | MPA polygon geometry + STRtree |
| `rasterio` | ≥1.3.0 | GeoTIFF tiling in ML pipeline |
| `pyproj` | ≥3.5.0 | Coordinate reprojection (UTM → WGS84) |
| `pillow` | ≥10.0.0 | PNG decode for inference |
| `numpy` | ≥1.24.0 | Array operations |
| `google-genai` | latest | Gemini API via Vertex AI |
| `react-leaflet` | — | Map rendering |
| `framer-motion` | — | UI animations |
| `lucide-react` | — | Icons |
