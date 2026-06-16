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
