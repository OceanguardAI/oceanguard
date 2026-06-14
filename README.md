# OceanGuard AI

> Satellite radar + AI to detect dark-fishing vessels in Marine Protected Areas. Decision-support for conservation officers — not an enforcement system.

---

## The Problem

Illegal, Unreported, and Unregulated (IUU) fishing drains an estimated **11–26 million tonnes** of fish from the ocean every year. Marine Protected Areas (MPAs) are the front line of ocean conservation, but the authorities watching them are chronically under-resourced.

The worst offenders run "dark" — they switch off their AIS transponders so they vanish from public vessel-tracking systems. AIS cannot find them. But **satellite SAR radar sees every vessel**, regardless of what it is broadcasting.

A vessel that appears in SAR imagery with **no matching AIS broadcast**, sitting **inside or near a Marine Protected Area**, is a high-value lead for a conservation patrol. Today, finding those leads means an analyst manually cross-referencing satellite scenes against AIS feeds — which does not scale.

**OceanGuard automates that cross-reference.**

---

## What It Does

1. A custom-trained deep-learning model (YOLO11n, mAP50 **0.838**) detects vessel-like objects in raw Sentinel-1 SAR imagery.
2. Each detection is georeferenced (pixel → real-world lat/lon).
3. Detections are cross-checked against AIS / dark-vessel data (Global Fishing Watch), MPA boundaries (WDPA), and nearby ports (OpenStreetMap).
4. A **deterministic, auditable risk-scoring engine** produces a 0–1 score and a LOW / MEDIUM / HIGH / CRITICAL level.
5. A **Claude AI layer** explains each case in plain language, briefs the officer, answers questions, and recommends patrol priorities.
6. A human conservation officer makes the final call. **OceanGuard never accuses or enforces — it flags for review.**

---

## System Architecture

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
  (SAR→640px)  (YOLO best.pt) (pixel→lat/lon)
                                    │
                                    ▼
                           risk.py (RISK ENGINE — deterministic)
              inputs: detection conf · AIS match · MPA distance · port dist
              output: risk_score, risk_level, structured evidence
──────────────────────────────────┬─────────────────────────────────────
                                  │ writes risk_events.json
                                  ▼
                    risk_events.json / SQLite (the "store")
                                  │
                                  ▼
────────────────────────────────────────────────────────────────────────
                   BACKEND  (FastAPI — Python)

  REST API                          AGENT LAYER (Anthropic API)
  ── GET  /health                   ── POST /agents/narrate
  ── GET  /detections               ── POST /agents/briefing
  ── GET  /risk-events              ── POST /agents/patrol
  ── GET  /risk-events/{id}         ── POST /agents/ask
  ── POST /risk-events/{id}/review        (tool-calling Q&A)
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
────────────────────────────────────────────────────────────────────────
                                  │
                                  ▼
                     Conservation Officer (decides)
```

---

## Two Independent Proofs

### Proof A — Technology Validation (Model Metrics page)
Custom YOLO11n trained on **HRSID** dataset (mAP50 = **0.838**), run on a real Sentinel-1 SAR scene from xView3 (`590dd08f71056cacv`, Gulf of Guinea). Produced **122 vessel detections**, confidences up to 0.76, fully georeferenced. Proves the detector generalises to raw, real-world SAR imagery.

### Proof B — Decision-Support for Bar Reef (Map Dashboard)
Global Fishing Watch's SAR-derived dark-vessel dataset provides **4 real unmatched detections** near Bar Reef Marine Sanctuary, Sri Lanka — including one **0.4 km from the sanctuary boundary**. Combined with the WDPA MPA polygon and OSM port data → risk scores → evidence cards.

> "Here is our detection technology proven on real SAR imagery, and here is how it applies to flag actual dark-fishing risk at a protected reef — using the same class of SAR-derived data, end to end, with a human in the loop."

---

## Tech Stack

| Layer | Choice |
|---|---|
| Detection model | Ultralytics YOLO11n |
| Geospatial | rasterio + pyproj + shapely |
| Backend | FastAPI + Pydantic v2 |
| AI agents | Anthropic Python SDK (claude-opus-4-8) |
| Store (MVP) | JSON file in memory |
| Frontend | React 18 + Vite + TypeScript |
| Map | react-leaflet (CartoDB DarkMatter, no API key) |
| Charts | recharts |
| Icons | lucide-react |
| Styling | Tailwind CSS |
| Deploy | Docker + docker-compose |

---

## Local Run

### Prerequisites
- Docker + docker-compose
- An Anthropic API key (agents work with a fallback even without one)

### Steps

```bash
git clone <repo-url>
cd oceanguard-ai

# Copy env file and add your API key
cp .env.example .env
# Edit .env: ANTHROPIC_API_KEY=sk-ant-...

# Generate risk events from cached data
cd ml
pip install -r requirements.txt
python build_risk_events.py
cp outputs/risk_events.json ../backend/data/

# Run full stack
cd ..
docker-compose up
```

- Backend API: http://localhost:8000
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

### Dev without Docker

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

## Demo Path

**Map → click the bar-reef-003 marker (8.51°N 79.68°E, 0.4 km from Bar Reef MPA) → Evidence Card (score 0.61 / HIGH) → "Get AI Explanation" → Patrol Board ranks it #1.**

---

## Artifact Files Required

Place these files before running `build_risk_events.py`:

| File | Path |
|---|---|
| YOLO11n weights | `ml/models/best.pt` |
| Bar Reef MPA polygon | `ml/data/bar_reef.geojson` |
| GFW dark-vessel data | `ml/data/gfw_bar_reef_sar_unmatched.json` |
| OSM port data | `ml/data/overpass_bar_reef_ports.json` |
| xView3 georef detections | `ml/outputs/detections_scene1_georef.json` |

---

## Deployment

- **Backend** → Google Cloud Run (`docker build ./backend && gcloud run deploy`)
- **Frontend** → Vercel or Netlify (connect repo, set `VITE_API_URL` to backend URL)

---

## Responsible AI

OceanGuard is a **decision-support tool**, not an enforcement system. It flags vessel detections for human review. It never identifies individuals, never accuses, and never triggers enforcement actions. All decisions are made by conservation officers with full access to the evidence trail.

See [docs/responsible-ai.md](docs/responsible-ai.md) for the full responsible-AI statement.

---

## Data Sources

| Source | Role |
|---|---|
| [HRSID](https://github.com/chaozhong2010/HRSID) | Model training dataset |
| [xView3-SAR](https://iuu.xview.us/) | Real SAR validation scene |
| [Global Fishing Watch API](https://globalfishingwatch.org/our-apis/documentation) | Dark-vessel + AIS data |
| [WDPA / Protected Planet](https://www.protectedplanet.net) | MPA boundaries |
| [OSM Overpass](https://overpass-api.de) | Port locations |
| [Ultralytics YOLO11](https://docs.ultralytics.com) | Detection framework |
| [Anthropic API](https://docs.anthropic.com) | AI agent layer |

---

## License

MIT
