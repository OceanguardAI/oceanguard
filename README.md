# OceanGuard AI

OceanGuard AI is an agent-driven decision-support system that detects "dark" (non-broadcasting) vessels inside Marine Protected Areas (MPAs).

It fuses Synthetic Aperture Radar (SAR) object detection, Automatic Identification System (AIS) tracking data, and spatial logic (MPA and coastal boundaries) to identify and risk-score suspicious vessels.

## Project Structure

- `ml/` - Offline data pipeline (SAR Tiling, YOLO Inference, Spatial Enrichment). Generates `risk_events.json`.
- `backend/` - FastAPI service providing the data API and Gemini-powered Agents (Narrator, Briefing, Patrol, Ask).
- `frontend/` - React/Vite/Tailwind dashboard for monitoring detections and interacting with AI agents.

## Quickstart

### 1. Generate ML Output
```bash
cd ml
pip install -r requirements.txt
python run_full_ml_workflow.py
python report_ml_status.py
```

See `ml/README.md` for the full ML workflow, temporary artifact handling, raw `.tif` inference, and verification commands.

### 2. Run Backend
```bash
cd backend
pip install -r requirements.txt
# Optional: Set GEMINI_API_KEY in .env for full agentic features
uvicorn app.main:app --reload --port 8000
```

See `backend/README.md` for the full backend route map, review persistence behavior, agent endpoints, and verification steps.
See `API_SETUP.md` for the Gemini Developer API key setup flow, or `GCP_GEMINI_SETUP.md` for the Google Cloud / Vertex-style Gemini path.

### Vertex AI Quick Test
```bash
gcloud config set project oceaneyelabs
gcloud auth application-default login
gcloud auth application-default set-quota-project oceaneyelabs
pip install -r requirements.txt
python test_vertex.py
```

### 3. Run Frontend
```bash
cd frontend
npm install
npm run dev
```

Or run everything with Docker:
```bash
docker-compose up --build
```

The Docker setup uses `backend/data` as the shared writable runtime data directory, so ML outputs copied there and review-status updates made through the UI both persist across container restarts.

## Live System

The production system runs on Google Cloud Run (`asia-south1`, project `oceaneyelabs`):

| Service | URL |
|---|---|
| Backend API | `https://oceanguard-api-ezas7zp4yq-el.a.run.app` |
| YOLO inference | `https://oceanguard-yolo-ezas7zp4yq-el.a.run.app` |
| Frontend | Auto-deployed on push to `main` |

Push to `main` triggers auto-deploy. Use **Actions → Run workflow** for manual redeploys.

**Data sources in use:**
- [Global Fishing Watch](https://globalfishingwatch.org/our-apis/tokens) — global SAR dark-vessel detections (AIS-based, 7-day lookback, 600 events)
- [Copernicus Data Space (CDSE)](https://dataspace.copernicus.eu) — Sentinel-1 VV SAR chips for the evidence card and YOLO verification
- WDPA marine layer via ArcGIS — 10 800+ MPA polygons for spatial risk scoring

## Roadmap

### High-resolution CCM escalation (planned)

OceanGuard currently uses **Sentinel-1** (free, ~10–20 m/pixel, instant) for real-time SAR chips and YOLO verification. This is enough to detect vessels, but not enough to identify vessel type or produce evidentiary imagery.

The next imagery tier is **Copernicus Contributing Missions (CCM)** — commercial/national satellites that supplement the core Sentinels:

| Mission | Type | Resolution | Use case |
|---|---|---|---|
| TerraSAR-X / TanDEM-X | SAR | ~1–3 m/px | Detect small fishing skiffs invisible on Sentinel-1; also the native domain of the HRSID model |
| COSMO-SkyMed | SAR | ~1–3 m/px | Alternative high-res SAR |
| Pleiades / SPOT | Optical | ~0.5–1.5 m/px | Human-readable photo for enforcement reports |

**Planned flow:**

```
Sentinel-1 + YOLO  →  instant triage  (live today)
        ↓  officer confirms high-priority suspect
CCM order          →  "Request TerraSAR-X / Pleiades of this exact point"
        ↓
Evidentiary-grade confirmation for enforcement action
```

This is an **async escalation tier**, not a live feed — CCM scenes are ordered from archive or tasked (hours-to-days latency), with per-month quotas on the free tier.

Access requires CCM approval on your CDSE account: [Request CCM access](https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/auth?client_id=cdse-public&response_type=code&scope=openid&redirect_uri=https%3A//dataspace.copernicus.eu/account/confirmed/1)
