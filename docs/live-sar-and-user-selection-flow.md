# OceanGuard AI — Live SAR and User Selection Flow

## Purpose

This document explains, in detail, how OceanGuard currently:

- shows a live Sentinel-1 SAR image chip for a detection
- verifies a user-selected point against the latest available SAR data
- sweeps a user-selected map area against the latest available SAR data
- connects the frontend map interactions to the backend and model services

It also explains what "live" means in this system and what we should build next if we want richer operator-driven selections such as drawn polygons, patrol corridors, or named protected-area sweeps.

---

## 1. What "Live SAR" Means in OceanGuard

OceanGuard does **not** stream a real-time SAR video feed. That is not how Sentinel-1 works.

What we mean by "live" is:

- we use the **latest available Sentinel-1 SAR scene** for the requested point or area
- we fetch it **on demand at request time**
- we process that fresh SAR data through our own detection logic when the officer asks for it

So the system is "live" in the sense that:

- the request is made now
- the data is fetched now
- the model runs now

But the image itself is still based on the **most recent satellite pass**, not a continuous video stream.

This distinction matters for demos and for officer expectations.

---

## 2. Current Live Data Sources

OceanGuard uses two different SAR-related paths:

### A. Global Fishing Watch live detection feed

This is the main operational detection feed.

- Source: Global Fishing Watch SAR dark-vessel API
- Purpose: provide candidate vessel detections at global scale
- Output into OceanGuard: `RiskEvent` objects in the in-memory repository
- Config:
  - `GFW_API_TOKEN`
  - `GFW_REGION_BBOX`
  - `GFW_LOOKBACK_DAYS`
  - `GFW_MAX_EVENTS`
  - `GFW_INGEST_ON_STARTUP`

This feed gives us detection points and metadata, not just raw imagery.

### B. Sentinel-1 SAR chip fetch

This is the on-demand imagery path.

- Source: Sentinel Hub Process API on Copernicus Data Space Ecosystem
- Purpose: fetch the actual radar image around a point
- Output into OceanGuard: PNG SAR chip
- Config:
  - `SENTINELHUB_CLIENT_ID`
  - `SENTINELHUB_CLIENT_SECRET`
  - `SENTINELHUB_TOKEN_URL`
  - `SENTINELHUB_PROCESS_URL`

This path is used when the UI wants to show a radar chip for a detection.

### C. YOLO verification service

This is the on-demand model inference path.

- Source: separate YOLO Cloud Run service
- Purpose: run our own ship detector on fresh SAR imagery
- Output into OceanGuard:
  - point verification result
  - area sweep contacts
  - optional agreement boost applied to an existing event
- Config:
  - `YOLO_SERVICE_URL`

This path is what powers "Run YOLO Check" and "Sweep Area".

---

## 3. High-Level Architecture

```text
Frontend map interaction
  -> frontend/src/App.tsx
  -> frontend/src/lib/api.ts
  -> FastAPI backend routes
  -> either:
     1. Sentinel Hub SAR chip fetch
     2. YOLO service point inference
     3. YOLO service area sweep
  -> backend response
  -> UI card / map overlay update
```

The frontend does not talk directly to Sentinel Hub or to the YOLO service. It always goes through the backend API.

That is the correct design because:

- secrets stay on the server
- request validation is centralized
- future logging, throttling, caching, and audit controls can live in one place

---

## 4. Flow A — How We Get the Live SAR Image for a Detection

This is the SAR chip shown in the Evidence Card.

### Frontend trigger

File: `frontend/src/components/EvidenceCard.tsx`

When a detection is selected:

1. the card checks `sarImageConfigured()`
2. if configured, it renders an image whose `src` is:
   - `sarImageUrl(event.lat, event.lon, event.timestamp)`

That URL resolves to:

```text
GET /sar-image?lat={lat}&lon={lon}&date={timestamp}
```

### Frontend API helper

File: `frontend/src/lib/api.ts`

- `sarImageConfigured()` -> calls `GET /sar-image/status`
- `sarImageUrl(lat, lon, date)` -> builds the chip URL

### Backend route

File: `backend/app/api/routes/sar.py`

- `GET /sar-image/status`
  - returns whether Sentinel Hub credentials are configured
- `GET /sar-image`
  - validates `lat`, `lon`, and optional `date`
  - calls `sentinel_sar.fetch_chip(...)`
  - returns PNG bytes
  - adds `Cache-Control: public, max-age=86400`

### Backend SAR service

File: `backend/app/services/sentinel_sar.py`

Current behavior:

- obtains an OAuth token from CDSE
- caches that token in memory
- builds a time window ending at the requested date
- uses a `12` day search window to improve the chance that a valid scene exists
- requests a `384 x 384` PNG chip
- centers the chip on the requested point
- uses a half-width of `0.05` degrees
- requests Sentinel-1 GRD, `IW` acquisition mode, `DV` polarization
- uses an evalscript to convert VV backscatter into a visible grayscale image

### Important practical meaning

The Evidence Card SAR image is:

- not a fake mock
- not a stored static asset
- not pre-rendered in the frontend

It is fetched live from Sentinel Hub when the card loads.

---

## 5. Flow B — If the User Selects a Single Point

This is the "Point scan" interaction.

### Current UI behavior

Files:

- `frontend/src/App.tsx`
- `frontend/src/components/MapView.tsx`

Flow:

1. officer taps or clicks `Point scan`
2. `scanMode` becomes `true`
3. `MapView` switches cursor/crosshair state
4. `ScanClickHandler` listens for the next map click
5. clicked map coordinates are sent back via `onScanPick(lat, lon)`
6. `App.tsx` calls `handleScanPick(lat, lon)`
7. frontend immediately calls:

```text
POST /verify/yolo?lat={lat}&lon={lon}&date={now}
```

### Frontend API helper

File: `frontend/src/lib/api.ts`

Function:

- `verifyYolo({ lat, lon, date?, eventId? })`

Important details:

- `eventId` is optional
- when the point comes from a random user click, there may be **no existing event**
- the API still works because it is coordinate-based, not event-based

This is exactly how arbitrary point selection connects to live data today.

### Backend route

File: `backend/app/api/routes/verify.py`

Route:

```text
POST /verify/yolo
```

It:

1. validates that `YOLO_SERVICE_URL` exists
2. forwards `{ lat, lon, date }` to the external YOLO service
3. receives model output
4. if `event_id` is present and the model found a ship:
   - reads the existing event from the repository
   - increases `risk_score` by `0.10`
   - appends `YOLO-confirmed (Sentinel-1)` to `matching_method`
   - updates the in-memory store only
5. returns:
   - `agreement`
   - raw YOLO result
   - optional updated event

### Why this is important

A user-selected point does **not** need to be one of the GFW detections.

That means the operator can:

- click inside an MPA
- click on open water
- click on a tip-off coordinate
- click near a suspicious cluster

and still ask the system:

"What does the latest available Sentinel-1 radar show here?"

---

## 6. Flow C — If the User Selects a Portion / Area

This is the "Sweep area" interaction.

### Current UI behavior

Files:

- `frontend/src/components/MapView.tsx`
- `frontend/src/App.tsx`

How it works today:

1. `BoundsReporter` listens to map move and zoom events
2. after every map move, it reports the current viewport bbox:
   - `[west, south, east, north]`
3. `App.tsx` stores that as `mapBounds`
4. when the officer clicks `Sweep area`, the frontend calls:

```text
POST /verify/yolo/sweep?min_lon=...&min_lat=...&max_lon=...&max_lat=...&date={now}
```

So the current "portion selection" is:

- **the visible map viewport**

It is not yet:

- a freehand polygon
- a lasso selection
- a custom rectangle drawn by dragging

### Backend sweep logic

File: `backend/app/api/routes/verify.py`

Route:

```text
POST /verify/yolo/sweep
```

Current behavior:

1. validates the bbox
2. converts the bbox into tile centers via `_tile_centers(...)`
3. uses:
   - `_SWEEP_TILE_DEG = 0.04`
   - `_SWEEP_MAX_TILES = 12`
   - `_SWEEP_WORKERS = 4`
4. sends each tile center to the YOLO service
5. gathers all detections
6. compares each detection with the existing live event store
7. marks each contact as:
   - `confirmed` if within `2 km` of a known event
   - `new` if not near any known event
8. returns summary counts and contact coordinates

### UI effect

The frontend renders:

- teal diamonds for confirmed contacts
- red pulsing diamonds for new contacts
- a rectangle over the swept area

That means a user-selected map portion is already connected to live SAR processing today, as long as the portion is the current viewport.

---

## 7. Step-by-Step Request Sequences

## A. Evidence Card SAR chip

```text
User clicks a detection
-> EvidenceCard mounts
-> frontend calls GET /sar-image/status
-> frontend sets img src to GET /sar-image?lat&lon&date
-> backend route calls sentinel_sar.fetch_chip(...)
-> Sentinel Hub returns PNG
-> backend streams PNG to browser
-> officer sees actual SAR chip
```

## B. User selects one point

```text
User clicks "Point scan"
-> scanMode=true
-> user clicks map at lat/lon
-> frontend calls POST /verify/yolo
-> backend forwards to YOLO service /detect-point
-> YOLO service fetches fresh Sentinel-1 SAR for that point
-> model runs inference
-> backend returns detections and agreement result
-> UI shows scan result panel
```

## C. User selects one area

```text
User pans/zooms map to desired area
-> BoundsReporter keeps latest viewport bbox in App state
-> user clicks "Sweep area"
-> frontend calls POST /verify/yolo/sweep
-> backend tiles bbox into <= 12 cells
-> backend fans out requests to YOLO service
-> YOLO analyzes each tile
-> backend merges contacts and compares with known events
-> UI shows confirmed/new markers
```

---

## 8. What Is Processed Where

### In the browser

The browser only:

- displays detections
- captures point or viewport selection
- sends API requests
- renders images and inference results

The browser does **not**:

- hold Sentinel Hub secrets
- run SAR processing
- run YOLO inference

### In the backend API

The backend:

- validates request parameters
- checks whether integrations are configured
- fetches live SAR chips through `sentinel_sar.py`
- proxies on-demand inference to the YOLO service
- applies agreement boost to existing events
- cross-matches sweep detections against the current live repository

### In the YOLO service

The separate YOLO service is responsible for:

- turning a point into a fresh SAR inference request
- running the model
- returning detections, confidence values, and chip data

Separating it from the main API is good because:

- Torch stays out of the main backend container
- scaling behavior can be managed independently
- failures in inference do not take down the core API

---

## 9. Current Constraints and Honest Limits

These details should be explained clearly in docs and demos.

### 1. Live does not mean continuous streaming

OceanGuard uses the latest available satellite pass, not a live video feed.

### 2. Point scan is exact, but depends on scene availability

If there is no suitable recent Sentinel-1 scene in the search window, the request may fail or return no useful contact.

### 3. Area sweep is currently viewport-based

Today, "selected portion" means:

- the current visible bounding box

It is not yet a custom-drawn polygon tool.

### 4. Area sweep is capped

To control time and cost:

- tile size is about `0.04°`
- maximum tiles per sweep is `12`
- if the requested viewport is large, the system samples more coarsely

That is why the response includes:

- `effective_tile_deg`
- `fully_covered`

### 5. YOLO agreement updates only the in-memory store

When a verification confirms a detection:

- the event score is updated in memory
- the seed file is not permanently rewritten for that temporary live decision

---

## 10. Recommended Next Build Plan for Richer User Selections

The current implementation already supports:

- arbitrary point selection
- viewport-based area selection

If we want richer operator-driven live SAR workflows, this is the recommended roadmap.

### Phase 1 — Document and polish what already exists

Goal:

- make current point scan and viewport sweep explicit in the UI and docs

Tasks:

1. rename `Sweep area` tooltip text to say it uses the visible map area
2. show the current bbox dimensions before launching a sweep
3. show whether the sweep is full coverage or sampled coverage
4. add a short explanation in the UI that SAR is "latest available pass", not live video

### Phase 2 — Add explicit rectangle selection

Goal:

- let the user drag a rectangle instead of relying only on the current viewport

Frontend:

1. add draw mode with Leaflet rectangle drawing
2. store `[minLon, minLat, maxLon, maxLat]`
3. preview selected area before submit

Backend:

1. reuse existing `/verify/yolo/sweep`
2. no route change required if we still submit bbox

This is the simplest and highest-value next step.

### Phase 3 — Add polygon selection

Goal:

- let users sweep irregular protected zones or hand-drawn shapes

Frontend:

1. allow polygon drawing
2. send polygon coordinates to backend

Backend:

1. add a new route such as `POST /verify/yolo/sweep-polygon`
2. derive tile centers inside polygon only
3. skip tiles outside polygon

Why this matters:

- better for MPAs that are not rectangular
- lower cost than sweeping the full bbox around a narrow area

### Phase 4 — Add named-area sweep

Goal:

- sweep a clicked MPA directly

Frontend:

1. allow click on MPA polygon
2. show action: `Sweep this MPA`

Backend:

1. fetch MPA geometry by feature id
2. tile inside that geometry

This is a strong demo feature because it matches the conservation workflow directly.

### Phase 5 — Add temporal controls

Goal:

- let the officer pick the acquisition time window

Frontend:

1. add date/time selector
2. default to latest available

Backend:

1. pass selected time into `/sar-image`, `/verify/yolo`, and `/verify/yolo/sweep`
2. keep existing fallback to `now`

This is useful for post-incident review and repeatability.

---

## 11. Recommended Messaging in the Product

To avoid confusion, the UI and demo narration should use wording like this:

- "Latest available Sentinel-1 SAR pass"
- "On-demand SAR verification"
- "Point scan"
- "Sweep visible area"

Avoid saying:

- "live satellite video"
- "real-time SAR stream"

because those are not technically correct.

---

## 12. Code Reference Map

### Frontend

- `frontend/src/App.tsx`
  - owns point scan, sweep, selection state, and panel behavior
- `frontend/src/components/MapView.tsx`
  - reports viewport bounds
  - captures map click point
  - draws scan marker, sweep rectangle, and sweep contacts
- `frontend/src/components/EvidenceCard.tsx`
  - requests and renders SAR chip
  - runs YOLO verification for existing detections
- `frontend/src/lib/api.ts`
  - central API client for SAR chip, point verification, and area sweep

### Backend

- `backend/app/api/routes/sar.py`
  - serves SAR chip status and chip PNG
- `backend/app/services/sentinel_sar.py`
  - handles Sentinel Hub token and Process API calls
- `backend/app/api/routes/verify.py`
  - handles point verification and area sweep
- `backend/app/store/repository.py`
  - holds current live event store used for sweep matching and agreement boost
- `backend/app/core/config.py`
  - configuration surface for GFW, Sentinel Hub, YOLO, Gemini, and CORS

---

## 13. Bottom Line

OceanGuard already supports three useful live-SAR-connected user actions:

1. **select a detection** -> fetch a fresh SAR chip for that point
2. **select any point on the map** -> run on-demand YOLO verification on the latest SAR data there
3. **select the visible map portion** -> sweep that area with our model and surface confirmed vs new contacts

What we do **not** yet have is custom drawn geometry selection. That should be the next enhancement if we want a more advanced operator workflow.
