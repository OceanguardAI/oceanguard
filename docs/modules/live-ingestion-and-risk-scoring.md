# Live Ingestion and Risk Scoring Module

## 1. What this module does

This module is the core operational intake layer of OceanGuard.

It answers:

- where do live detections come from?
- when does the backend ingest them?
- how are they converted into `RiskEvent`s?
- why are some detections ranked above others?

The main files are:

- `backend/app/main.py`
- `backend/app/api/routes/ingest.py`
- `backend/app/services/gfw_ingest.py`
- `backend/app/store/repository.py`

## 2. The overall ingestion model

OceanGuard uses a seed-plus-live model.

That means:

### Seed layer

At startup, the backend immediately loads `backend/data/risk_events.json`.

This guarantees:

- the app has something to serve immediately
- the dashboard does not depend on external APIs for basic startup
- local/offline fallback still works

### Live layer

If live GFW ingest is enabled:

- the backend starts a background job
- that job fetches live detections
- the in-memory repository is replaced with fresh events

This is a practical design for Cloud Run because it avoids slow synchronous startup.

## 3. Why ingestion is backgrounded

This is one of the most important backend design decisions.

In `backend/app/main.py`, live ingest is pushed into a background thread using:

- `asyncio.create_task(...)`
- `asyncio.to_thread(...)`

Why:

- MPA index loading takes time
- global SAR fetch takes time
- Cloud Run health checks expect quick startup

If ingest happened in the blocking startup path, the service could fail health checks and restart repeatedly.

So the system deliberately chooses:

- fast health
- seed data immediately available
- live replacement a few seconds later

That is a very sensible cloud-runtime tradeoff.

## 4. The live detection source

The current operational live source is Global Fishing Watch SAR.

In `gfw_ingest.py`, the system requests:

- a report from the GFW 4wings endpoint
- over the configured bbox
- for the configured lookback window

Important settings:

- `GFW_API_TOKEN`
- `GFW_REGION_BBOX`
- `GFW_LOOKBACK_DAYS`
- `GFW_MAX_EVENTS`
- `GFW_INGEST_ON_STARTUP`

This is not raw radar imagery. It is a higher-level detection feed.

That means GFW already does some heavy work for us:

- it identifies SAR vessel detections
- it performs server-side SAR/AIS matching

OceanGuard then adds its own interpretation layer.

## 5. How GFW rows become `RiskEvent`s

This happens in `backend/app/services/gfw_ingest.py`.

The path is:

1. call `_fetch_sar_report()`
2. flatten the response into raw detection rows
3. convert each row using `_to_risk_event(...)`
4. sort by risk
5. deduplicate by coarse geographic cell
6. optionally stratify/cap the final set
7. renumber IDs into display order

### Why `_to_risk_event()` matters

This function is the semantic bridge from external provider data to internal product objects.

It adds:

- `lat` / `lon`
- AIS match state
- MPA proximity
- port proximity
- risk score
- risk level
- recommended action
- review status
- human-readable why-flagged text

This is where OceanGuard becomes a product rather than a feed proxy.

## 6. How "dark vessel" is determined

In this live feed path, a vessel is treated as AIS-matched if GFW supplies identity fields such as:

- `vesselId`
- `mmsi`
- `shipName`

If those identity fields are absent:

- the system treats it as a dark detection candidate

This is important:

OceanGuard does not invent the AIS mismatch in this path.

It interprets GFW's existing server-side match/no-match output.

## 7. The live risk score

The live operational risk score is implemented in `gfw_ingest.py` through `_score_detection(...)`.

Current logic:

- baseline SAR vessel presence: `0.25`
- no AIS match: `+0.20`
- inside MPA: `+0.45`
- within 10 km: `+0.30`
- within 50 km: `+0.15`
- repeated presence: `+0.05`
- cap at `0.99`

Current thresholds:

- `CRITICAL >= 0.80`
- `HIGH >= 0.60`
- `MEDIUM >= 0.45`
- else `LOW`

### Why this formula makes sense

The model is designed so MPA proximity is the strongest factor.

That reflects the product's conservation use case:

- a vessel in open ocean is not necessarily suspicious
- a dark vessel inside or very near a protected area is far more operationally relevant

This is a transparent domain heuristic, not a hidden learned ranking.

## 8. Why the system deduplicates global detections

After scoring, the system keeps only the highest-risk detection per approximately `0.5°` cell.

Why:

- global queries can return huge clustered result sets
- a pure top-N cap would over-concentrate on a few hotspots
- the map would look fake or unreadable

Then the system applies stratified sampling across risk levels.

Why stratify:

- a global top-N would often be almost entirely CRITICAL markers
- that is not a realistic picture of the global risk distribution
- the UI needs both top threats and a readable spread

This is a product-shaping decision, not just a performance trick.

## 9. The in-memory repository

`backend/app/store/repository.py` is the current live state holder.

It supports:

- `load()`
- `save()`
- `replace_all()`
- `upsert_many()`
- `all()`
- `get()`
- `update_review()`
- `summary()`

### Why the repository matters

The repository is the shared truth that multiple parts of the app read from:

- dashboard event list
- summary counts
- agent prompts
- YOLO agreement updates
- sweep contact comparison

### Important behavior

Live ingest often uses:

- `persist=False`

That means:

- the in-memory state changes
- the seed handoff file is preserved as fallback

This is intentional and useful for a demo/cloud environment.

## 10. Manual ingestion and external push

The ingest route file exposes two important operational tools.

### `POST /ingest/gfw`

Use this when you want to manually refresh from GFW.

It:

- fetches new events
- replaces the repository
- returns counts of dark vs AIS-matched detections

### `POST /ingest/push`

Use this when another system computes events externally and wants the backend to receive them.

Modes:

- `merge`
- `replace`

This is a useful extension seam for future pipelines.

## 11. Relationship to AIS sampling

There is also a separate AIS support module in `ais_stream.py`.

That module is not the main global ingest.

Its role is:

- sample live AIS over the configured bbox
- help confirm whether a SAR contact truly has no nearby AIS vessel

This is a secondary evidence layer, not the primary event source.

## 12. Relationship to the offline ML pipeline

There are two different scoring worlds in the repo:

### Live backend scoring

- implemented in `backend/app/services/gfw_ingest.py`
- optimized for operational live GFW detections

### Offline ML scoring

- implemented in `ml/pipeline/risk.py`
- optimized for artifact generation from the offline workflow

They are related conceptually, but they are not identical implementations.

That distinction is important for learning the project correctly.

## 13. If you want to modify this module

### Change the live risk formula

Start with:

- `backend/app/services/gfw_ingest.py`

Then also verify:

- frontend expectations
- documentation
- any tests that assert risk behavior

### Change ingest startup behavior

Start with:

- `backend/app/main.py`

### Add a new live provider

Start with:

- `backend/app/api/routes/ingest.py`
- `backend/app/services/`
- `backend/app/store/repository.py`

## 14. Bottom line

This module is the operational heart of OceanGuard.

It converts:

- external live SAR detections

into:

- ranked, reviewable, explainable product events

without making the system dependent on slow startup or opaque scoring.
