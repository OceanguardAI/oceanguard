# OceanGuard AI — Beginner's Guide

> Start here if you are new to this project. No prior knowledge of satellites, ocean science, or machine learning is assumed.

---

## 1. The Problem We Are Solving

### What is IUU fishing?
IUU stands for **Illegal, Unreported, and Unregulated** fishing. It means fishing in places you are not allowed, catching more than you declared, or fishing with no oversight at all. It costs the world an estimated 11–26 million tonnes of fish per year and destroys marine ecosystems.

### What is a Marine Protected Area (MPA)?
A Marine Protected Area is a region of ocean where fishing is restricted or banned — like a national park, but underwater. Examples include coral reefs, breeding grounds, and endangered habitat zones. Bar Reef Marine Sanctuary in Sri Lanka is the MPA used in this project. These zones have legal boundaries on paper, but nobody is watching them continuously.

### Why can't we just track ships?
Most ships broadcast their location using a system called **AIS** (Automatic Identification System) — a radio signal ships transmit so they don't crash into each other. But a vessel that wants to fish illegally can simply **turn off the AIS transmitter**. When they do, they disappear from every public tracking system. We call this a **"dark vessel"**.

### What is the solution?
Physics. A ship's metal hull reflects radar waves regardless of whether the transponder is on. **SAR (Synthetic Aperture Radar)** satellites beam microwave pulses at the ocean and measure the reflection. Metal vessels appear as bright spots. **The ship cannot opt out of reflecting radar.**

OceanGuard uses this principle: it cross-references what the satellite radar sees with what AIS reports. If the radar sees a vessel that AIS doesn't know about → possible dark vessel → human officer investigates.

---

## 2. Key Concepts (Plain English)

| Term | What it means |
|---|---|
| **SAR** | Satellite radar that sees ships through clouds and at night, using microwave signals |
| **AIS** | Radio broadcast ships use to announce their position. Can be switched off. |
| **Dark vessel** | A ship visible on SAR radar but with no matching AIS broadcast |
| **MPA** | Marine Protected Area — a protected ocean zone like a national park |
| **GFW** | Global Fishing Watch — a nonprofit that processes SAR imagery and provides a live API of dark-vessel detections |
| **YOLO** | "You Only Look Once" — a fast machine learning model that finds objects in images. We trained ours to find ships in SAR images. |
| **Risk score** | A number between 0 and 1. The higher it is, the more suspicious the detection. Calculated by a fixed formula. |
| **Evidence card** | A summary card for one detection: where it is, how confident the radar was, whether AIS is absent, how close it is to an MPA |
| **Gemini** | Google's AI model that reads the evidence and writes plain-English explanations for officers |

---

## 3. How the System Works (Step by Step)

### Step 1 — Satellite radar images the ocean
Sentinel-1 satellites (operated by the European Space Agency) orbit Earth and send radar pulses at the ocean. Bright spots in the image = ship-sized objects. GFW processes millions of these and builds a database of detections.

### Step 2 — Cross-check against AIS
GFW compares each radar detection to nearby AIS broadcasts. If a bright spot has no matching AIS signal within 2 km and 3 hours → flagged as a **dark vessel candidate**.

### Step 3 — OceanGuard ingests this feed
At startup, the OceanGuard backend calls the GFW API and loads the latest dark-vessel detections into memory. This happens automatically — no manual step needed.

### Step 4 — Risk scoring
For each detection, the system calculates a risk score using a fixed formula:
- How confident was the radar detection? (30%)
- Was AIS absent? (25%)
- Is the vessel near or inside an MPA? (25%)
- Does GFW show fishing activity patterns? (10%)
- Has this location been flagged before? (10%)

This formula is fully transparent — every number can be checked by hand.

### Step 5 — Gemini explains it
Google's Gemini 2.5 Flash AI model reads the risk score and evidence and writes a 2–3 sentence plain-English explanation: why this was flagged, and what is uncertain about it.

### Step 6 — Human officer reviews
The dashboard shows a color-coded map (green = low risk → red = critical). Officers click a detection to see the full evidence card, read the AI explanation, and decide: Confirmed Risk, False Positive, or Resolved. **The AI never makes the final call.**

### Step 7 — On-demand YOLO verification (optional)
An officer can click "Run YOLO Check" to run our own trained AI model on the live satellite radar image for that exact location. This independently confirms or denies the detection. Two independent systems agreeing raises the risk score by +0.10.

---

## 4. System Architecture (Simple View)

```
[Sentinel-1 Satellite]
        │ radar images
        ▼
[Global Fishing Watch API]  ←── server-side AIS cross-match
        │ dark vessel detections (lat/lon, confidence, AIS status)
        ▼
[OceanGuard Backend (FastAPI)]
        │
        ├── Risk scoring (deterministic formula)
        │
        ├── MPA check (is vessel near a protected area?)
        │
        ├── Gemini AI agents (explain, brief, rank, answer questions)
        │
        └── YOLO verify (on-demand: fetch Sentinel-1 chip → run our own model)
                │
                ▼
[OceanGuard Dashboard (React)]
        │
        ├── Map: colored dots showing vessel detections
        ├── Evidence Card: full detail per detection
        ├── Daily Briefing: AI-written threat summary
        ├── Patrol Board: top 3 locations to investigate
        └── Ask OceanGuard: chat with the AI analyst
                │
                ▼
[Conservation Officer → decides]
```

---

## 5. The Technology Stack (What Each Tool Does)

| Tool | What it is | Why we use it |
|---|---|---|
| **Python** | Programming language | Used for the backend, ML pipeline, and data processing |
| **FastAPI** | Web framework for Python | Quickly builds the API that the frontend talks to |
| **YOLO11n** | Machine learning model | Trained to find ships in radar images |
| **PyTorch** | ML library | Runs the YOLO model |
| **Shapely** | Geometry library | Checks if a point is inside an MPA polygon |
| **React** | JavaScript UI library | Builds the dashboard you see in the browser |
| **TypeScript** | Typed JavaScript | Catches bugs before they reach production |
| **Tailwind CSS** | Styling tool | Makes the UI look good with utility classes |
| **Leaflet** | Map library | Shows the interactive ocean map with vessel dots |
| **Framer Motion** | Animation library | Smooth animations on the landing page |
| **Gemini 2.5 Flash** | Google AI model | Writes plain-English briefings and answers officer questions |
| **GFW API** | External data service | Provides live SAR dark-vessel detections |
| **AISStream.io** | External data service | Provides live AIS vessel broadcasts |
| **Sentinel Hub** | Satellite imagery API | Fetches Sentinel-1 radar chips for on-demand YOLO verify |
| **WDPA** | Protected area database | Provides MPA boundary polygons (no login needed) |
| **Docker** | Container tool | Packages the app so it runs the same everywhere |
| **Google Cloud Run** | Cloud hosting | Runs the backend and frontend in production |
| **GitHub Actions** | CI/CD pipeline | Automatically deploys when code is pushed to main |

---

## 6. Project Structure at a Glance

```
OceanEye/
├── ml/           ← Machine learning: train model, run inference on SAR images
├── backend/      ← Python API: serves data, runs AI agents, connects to live feeds
├── frontend/     ← React dashboard: the UI officers use
└── docs/         ← Technical documentation
```

Each folder is independent. You can work on the frontend without understanding the ML pipeline, and vice versa.

---

## 7. Running the Project Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker Desktop (optional but easiest)

### Quickstart with Docker
```bash
# 1. Copy the example env file
cp backend/.env.example backend/.env

# 2. Add your API keys to backend/.env
# At minimum: GEMINI_API_KEY and GFW_API_TOKEN

# 3. Start everything
docker-compose up

# Dashboard: http://localhost:5173
# API docs:  http://localhost:8000/docs
```

### Without Docker
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

### API keys you need
| Key | Where to get it | Required? |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio (aistudio.google.com) | Yes (for AI features) |
| `GFW_API_TOKEN` | globalfishingwatch.org/our-apis | Yes (for live detections) |
| `AISSTREAM_API_KEY` | aisstream.io | Optional (for AIS cross-check) |
| `SENTINELHUB_CLIENT_ID/SECRET` | dataspace.copernicus.eu | Optional (for YOLO verify) |

The dashboard works without the YOLO service — it will just show "YOLO not configured" on the verify button.

---

## 8. Dashboard Features — What Each Button Does

| Feature | Where | What it does |
|---|---|---|
| **Map dots** | Main page | Each dot = one dark vessel detection. Color = risk level (green/yellow/orange/red) |
| **Click a dot** | Map | Opens the Evidence Card for that detection |
| **Run YOLO Check** | Evidence Card | Fetches the real Sentinel-1 radar image and runs our AI model to independently verify |
| **Sweep Area** | Map controls | Scans everything currently visible on the map using YOLO — finds contacts the GFW feed may have missed |
| **Scan Mode** | Map controls | Click any ocean point to run YOLO at that exact location |
| **Briefing** | Sidebar | Gemini writes a plain-English summary of today's threat picture |
| **Patrols** | Sidebar | Gemini ranks the top 3 detections by patrol urgency with justification |
| **Ask OceanGuard** | Sidebar | Chat with the AI — ask any question about the current detections |
| **Review buttons** | Evidence Card | Confirm Risk / False Positive / Resolved — this is the human decision step |
| **ML Validation** | Top nav | Shows the YOLO model's training metrics and performance on real satellite data |
| **Data Resources** | Top nav | Documents every data source used and its trust level |

---

## 9. Understanding the Risk Score

Every detection gets a score from 0 to 1. Here is how to read it:

| Score | Level | Color | Meaning |
|---|---|---|---|
| 0.00 – 0.34 | LOW | 🟢 Green | Weak signal, low confidence, or far from any MPA |
| 0.35 – 0.54 | MEDIUM | 🟡 Yellow | Some concerning signals but not urgent |
| 0.55 – 0.74 | HIGH | 🟠 Orange | Dark vessel near an MPA — patrol recommended |
| 0.75 – 1.00 | CRITICAL | 🔴 Red | Dark vessel inside or very close to MPA — immediate review |

**The score is never a guess.** It is computed from the exact formula in `docs/data-dictionary.md`. Any officer can verify it by hand.

---

## 10. What the AI Does (and Does Not Do)

**Gemini AI does:**
- Write plain-English explanations of each detection
- Write the daily threat briefing
- Rank patrol priorities
- Answer officer questions about the data

**Gemini AI does NOT:**
- Calculate the risk score (that is a fixed formula)
- Make enforcement decisions
- Access satellite imagery directly
- Identify who is on a vessel

**The system never accuses.** It describes observable sensor evidence and leaves all judgement to the human officer. A vessel with no AIS could have a broken transponder — the system always notes this uncertainty.

---

## 11. Further Reading

| File | What it covers |
|---|---|
| `LIVE_DATA.md` | How to set up and operate the live data feeds |
| `docs/architecture.md` | Full system architecture with data flow diagrams |
| `docs/data-dictionary.md` | Every field in the risk event, risk formula with worked example |
| `docs/responsible-ai.md` | How the system handles fairness, bias, and human oversight |
| `ml/README.md` | How to run the offline ML pipeline (SAR inference + risk events) |
| `backend/app/api/routes/` | The actual API code — readable FastAPI routes |
| `backend/app/agents/` | The Gemini agent code — how briefing/patrol/ask work |
