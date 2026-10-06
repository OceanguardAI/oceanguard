# OceanGuard AI — Complete Project Context

**Last updated: 2026-10-06**
Copy-paste this entire file into a new chat to continue working on the project.

---

## 1. What This Project Is

**OceanGuard AI** is a maritime dark-vessel detection and alerting system built as an academic/research project. It detects vessels that have switched off their AIS transponders ("dark vessels") near marine protected areas (MPAs), using:

- **Global Fishing Watch (GFW) API** — SAR (satellite radar) aggregate vessel presence data
- **YOLO11n deep-learning detector** — on-demand verification on real Sentinel-1 SAR imagery
- **Gemini 2.5 Flash** — AI agents for daily briefings, patrol planning, and Q&A
- **React + FastAPI** — dashboard frontend + REST backend

The project is in development. It is NOT deployed to any cloud. The local `docker compose` path is the demo path.

---

## 2. Repository Layout

```
D:\PROJECTS\AI_ML\OceanEye\
├── backend/                  FastAPI backend (Python 3.11)
│   ├── app/
│   │   ├── agents/           ask.py, briefing.py, helpers.py  (Gemini agents)
│   │   ├── api/routes/       ingest.py, verify.py, risk_events.py, ...
│   │   ├── core/             config.py (Settings via pydantic-settings)
│   │   ├── models/           schemas.py  (Pydantic models)
│   │   ├── services/         gfw_ingest.py, sentinel_sar.py, mpa_index.py, ...
│   │   ├── store/            operational.py (in-memory), postgres.py
│   │   └── tools/            compare_gfw_versions.py
│   ├── data/
│   │   └── risk_events.json  126 SEED events (2024-01-15) — NOT live data
│   └── tests/                118 passing tests
├── frontend/                 React 18 + Vite + TypeScript + Tailwind + Leaflet
├── yolo-service/             FastAPI service that runs YOLO inference
│   └── app/main.py           Loads ml/models/best.pt
├── ml/
│   ├── models/best.pt        YOLO11n weights (HRSID fine-tune, mAP@50=0.838)
│   ├── evaluation/
│   │   └── detection_by_size.py   Size-binned recall evaluator (CLI + library)
│   ├── cloud/
│   │   ├── fetch_xview3.py   Downloads xView3 scenes inside Azure ML job
│   │   └── requirements-eval.txt
│   ├── pipeline/tiling.py    SAR tiling (dB [-50,0] VH)
│   └── tests/                53 passing tests
├── scripts/
│   ├── azure_setup.ps1       Provisions Azure ML workspace (centralindia)
│   └── azure_eval_job.ps1    Submits baseline eval job to Azure ML
└── docs/
    ├── PROJECT_CONTEXT.md    ← THIS FILE
    ├── architecture.md       System design (updated Oct 2026)
    ├── gfw-v5-migration.md   GFW v4→v5 runbook (15 days remaining)
    ├── small-vessel-detection-plan.md
    ├── agent-architecture-plan.md
    └── literature-review.md
```

---

## 3. Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11, FastAPI, pydantic-settings, httpx, shapely, rasterio |
| Frontend | React 18, TypeScript, Vite, Tailwind, Leaflet, Recharts, Framer Motion |
| ML | YOLO11n (ultralytics), PyTorch (CPU), rasterio |
| AI agents | Gemini 2.5 Flash via `google-genai` SDK (`GEMINI_API_KEY`) |
| Data sources | GFW API v3, Sentinel Hub / CDSE, AISStream.io, WDPA ArcGIS |
| Infra | Docker Compose (local demo), Azure ML (eval/train), no cloud deploy active |

---

## 4. Live Data Status — HONEST

| Source | Status | Details |
|---|---|---|
| **GFW SAR cells** | ⚠️ Partial | API call works if `GFW_API_TOKEN` in `.env`; returns raw `ActivityAggregate` cells (not scored `RiskEvent`s) |
| **Risk scoring** | ❌ Removed | Was removed in commit `8f07b9e` (25 Sep 2026). Seed JSON has pre-set scores |
| **AIS cross-match** | ❌ Removed | `ais_matched` is hard-coded `False`. AISStream key in config but cross-match code removed |
| **Dashboard events** | ❌ Seed data | All 126 events from `backend/data/risk_events.json`, dated 2024-01-15 |
| **YOLO verify (single)** | ✅ Works | `POST /verify/yolo` → Sentinel Hub → real SAR chip → `best.pt` |
| **YOLO sweep** | ✅ Works | `POST /verify/yolo/sweep` → tiles bbox → 4 parallel workers |
| **Gemini agents** | ✅ Work | Briefing / Ask / Patrol all functional, reasoning over seed events |
| **Database** | ❌ Not connected | `database_url=""` in config; in-memory only; data lost on restart |
| **GFW dataset pin** | ✅ Done | Pinned to `public-global-sar-presence:v4.0` in `config.py` and env |

**Bottom line:** The GFW API connection exists but the pipeline is broken in the middle (no scoring, no DB). The map and KPIs show 2024 seed data.

---

## 5. The YOLO Model — Full Details

### What was trained
- **Architecture:** YOLO11n (nano — ~2.6M params, fastest YOLO11 variant)
- **Training dataset:** HRSID (High-Resolution SAR Image Dataset)
  - 5,604 SAR ship images, ~0.5–3 m pixels
  - 2,857 train / 715 val split (by scene, not tile)
  - 50 epochs, SGD optimizer
- **Reported metrics (HRSID test set):**
  - mAP@50 = **0.838**
  - mAP@50-95 = **0.579**
  - Precision = **0.830**
  - Recall = **0.818**
- **Weights file:** `ml/models/best.pt`

### The critical gap
- HRSID pixels = 0.5–3 m. Live **Sentinel-1 GRD** = **10 m pixels**, 20×22 m resolution.
- The model has **never been run on real Sentinel-1 imagery.** The 0.838 mAP is on its own training distribution.
- Small vessels (<30 m) that are 5–15 px wide in HRSID → 2–5 px in Sentinel-1. Likely missed.
- Three different intensity mappings exist: `tiling.py` uses dB [-50,0] VH; `yolo-service` uses 2.5×VV linear; HRSID conversion undocumented.

### Previous training vs plan
- **Previous:** fine-tuned YOLO11n on HRSID. Good HRSID metrics. Never tested on Sentinel-1.
- **Now (Step 1):** run `best.pt` on xView3 validation scenes (real Sentinel-1, human labels, vessel lengths) → size-binned recall report. No training.
- **Later (Step 2, only if gap is large):** fine-tune from `best.pt` on xView3 train + HRSID mix. Accept new model only if it improves ≥1 size bin AND HRSID mAP drops ≤0.02.
- **Training needs GPU.** Azure student subscription has zero T4 quota. Use Colab/Kaggle T4 for training.

---

## 6. Azure ML Infrastructure

| Resource | Value |
|---|---|
| Subscription | `901ad003-54c0-474f-bea8-cc3a36034d0c` (Azure for Students) |
| Account | `thanoba-cs22067@stu.kln.ac.lk` |
| Resource group | `oceanguard-rg` |
| Region | `centralindia` (only allowed region with ML workspace support) |
| ML Workspace | `oceanguard-ml` |
| Storage | `oceanguardmldata` |
| Container Registry | `fbb0b9f906c84dbe817c488f10b6882a` (Basic, created manually) |
| CPU Cluster | `cpu-eval` (Standard_DS3_v2, min=0 nodes) |
| GPU Quota | **0** — student subscription, increases refused by Azure policy |

**Registered data assets:**
- `xview3-smoke` — synthetic 3-vessel scene (smoke test only)
- `yolo11n-best` — `best.pt` model weights (version 2 = SHA `ff2472160157`)

**Smoke test result:** Job `gifted_seed_crb4qvtcw0` completed. Synthetic 3-vessel scene → 1/3 recall, 0 FP. Pipeline end-to-end works.

**Real xView3 baseline:** NOT run yet. Blocked on xView3 scene download.

---

## 7. xView3 Dataset

- **Host:** `iuu.xview.us` (NOT `iuu.xview3.ai`)
- **xView3 account:** `thanobansk@gmail.com`
- **Licence:** scenes cannot be downloaded inside cloud jobs (licence forbids it). User must click "I agree" + download manually.
- **Size:** ~1.3 TB train / ~123 GB validation. We need only 2–3 validation scenes (~3–5 GB each).
- **Scene format:** `<scene_id>/VH_dB.tif` (and `VV_dB.tif`)
- **Labels:** one CSV per split: `scene_id`, `detect_scene_row`, `detect_scene_column`, `is_vessel`, `confidence` (HIGH/MEDIUM/LOW), `vessel_length_m`
- **Download process:** download scene `.tar.gz` + `labels.csv` from xview.us → run `scripts/azure_eval_job.ps1` to upload to Azure blob → submit eval job

---

## 8. GFW v5 Migration — URGENT (15 days)

- **Oct 21 2026:** GFW `latest` alias flips to pipeline v5. v4 stops updating.
- **Current code:** pinned to `:v4.0` ✅
- **Comparison NOT done yet** — needs `GFW_API_TOKEN` in `backend/.env`
- **Command:**
  ```bash
  cd backend
  .venv/Scripts/python.exe -m app.tools.compare_gfw_versions \
      --start 2026-08-01 --end 2026-08-31 \
      --bbox 79.4,8.0,79.9,8.8 \
      --out gfw_v4_vs_v5_barreef_aug.json
  ```
- After the comparison, decide tolerance → switch to `:v5.0` if within tolerance.

---

## 9. Security Gaps (before any public demo)

| Issue | Location | Fix |
|---|---|---|
| No auth on mutation routes | `/ingest/push`, `/ingest/gfw`, `/agents/*`, `/verify/*` | Set `ADMIN_API_KEY` in `.env` — code already supports it in `config.py` |
| CORS `*` on YOLO service | `yolo-service/app/config.py` | Lock to known frontend origin |
| `/ingest/push?mode=replace` wipes all data | `backend/app/api/routes/ingest.py` | Remove or require auth |
| No request size limits | FastAPI defaults | Add middleware |

---

## 10. Full Pending Work (prioritised)

### P0 — Before Oct 21 (15 days, no data needed)
- [ ] Run GFW v4 vs v5 comparison (needs `GFW_API_TOKEN`)
- [ ] Add `ADMIN_API_KEY` auth to mutation routes
- [ ] Fix `docker-compose.yml` so `docker compose up` produces a working local demo
- [ ] Label seed data honestly in UI (rename "GFW" seed events, show dates)

### P1 — xView3 baseline (needs scene download)
- [ ] Download 2–3 xView3 validation scenes from `iuu.xview.us` (user logs in, I upload)
- [ ] Run `scripts/azure_eval_job.ps1` with real scenes
- [ ] Get size-binned recall report for `best.pt` on real Sentinel-1

### P2 — Live pipeline
- [ ] Start PostgreSQL container (`docker compose up db`)
- [ ] Set `DATABASE_URL` in `backend/.env`
- [ ] Write `ActivityAggregate → RiskEvent` scoring function
- [ ] Wire: GFW ingest → scoring → DB → `/v1/risk-events` → UI

### P3 — Training (only if P1 shows large gap)
- [ ] Needs external GPU (Colab/Kaggle T4 — student Azure has no GPU quota)
- [ ] Fine-tune from `best.pt` on xView3 train + HRSID mix
- [ ] Acceptance gate: ≥1 bin improves, HRSID mAP drop ≤0.02, FP/100km² within limit

---

## 11. Security / Commit Rules

- Commits authored as `thanoban` only. **No Co-Authored-By trailers.**
- API keys in `.env` files (gitignored). Never hardcoded.
- Training only on Azure student account (`thanoba-cs22067@stu.kln.ac.lk`) or Colab/Kaggle. Never on local laptop.
- For Cloud Run (if re-enabled): keys in GitHub Secrets, config in GitHub Vars.

---

## 12. How to Run Locally

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # then fill in GFW_API_TOKEN, GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # → http://localhost:5173

# YOLO service (optional, for verification)
cd yolo-service
pip install -r requirements.txt
uvicorn app.main:app --port 8001

# Full stack
docker compose up   # (Docker Desktop must be running)
```

---

## 13. Key File Locations

| What | File |
|---|---|
| All settings / env vars | `backend/app/core/config.py` |
| GFW API call | `backend/app/services/gfw_ingest.py` |
| YOLO inference service | `yolo-service/app/main.py` |
| Risk event seed data | `backend/data/risk_events.json` |
| YOLO weights | `ml/models/best.pt` |
| Size-binned evaluator | `ml/evaluation/detection_by_size.py` |
| Azure eval job script | `scripts/azure_eval_job.ps1` |
| Azure setup script | `scripts/azure_setup.ps1` |
| GFW v4/v5 compare tool | `backend/app/tools/compare_gfw_versions.py` |
| Gemini Ask agent | `backend/app/agents/ask.py` |
| Frontend main entry | `frontend/src/App.tsx` |
| API routes | `backend/app/api/routes/` |

---

## 14. Research Questions (for academic write-up)

- **RQ1:** How do GFW SAR v4 and v5 detections differ over identical windows near MPAs?
- **RQ2:** What is the size-binned recall of a HRSID-trained YOLO11n on real Sentinel-1?
- **RQ3:** How much does xView3 fine-tuning improve small-vessel recall vs. HRSID baseline?
- **RQ4:** What is the false-alarm rate (FP/100 km²) at different confidence thresholds?
- **RQ5:** Can a tool-calling LLM agent accurately answer questions about live maritime data with source citations?
