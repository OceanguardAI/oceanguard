# OceanGuard AI

OceanGuard AI is an agent-driven decision-support system that detects "dark" (non-broadcasting) vessels inside Marine Protected Areas (MPAs).

It fuses Synthetic Aperture Radar (SAR) object detection, Automatic Identification System (AIS) tracking data, and spatial logic (MPA and coastal boundaries) to identify and risk-score suspicious vessels.

## Project Structure

- `ml/` - Offline data pipeline (SAR Tiling, YOLO Inference, Spatial Enrichment). Generates `risk_events.json`.
- `backend/` - FastAPI service providing the data API and Anthropic-powered Agents (Narrator, Briefing, Patrol, Ask).
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
# Optional: Set ANTHROPIC_API_KEY in .env for full agentic features
uvicorn app.main:app --reload --port 8000
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
