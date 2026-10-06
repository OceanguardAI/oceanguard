# OceanGuard End-to-End Development and Architecture Plan

Status: proposed implementation plan, not a statement that these capabilities are deployed. Reviewed and corrected on October 2, 2026; see section 1a. Last status check: October 6, 2026 — see `docs/PROJECT_CONTEXT.md` for current vs. intended state.

This is the main planning document for upgrading OceanGuard from a demo-style vessel detection dashboard into a research-grade and industry-ready maritime intelligence system. It is intentionally written as an implementation guide: another engineer or agent should be able to follow it without choosing a new architecture.

## 1. Product goal and scope

OceanGuard should find vessel observations, connect observations over time where evidence permits, compare them with AIS and geographic context, and help an analyst investigate explainable alerts. The system should be honest about uncertainty: a missing signal, expired provider, cloudy acquisition, sparse AIS sample, or low-confidence model result must appear as limited evidence, not as proof of vessel behavior.

There are two connected operating modes:

1. Satellite monitoring: search an area for available acquisitions, detect vessels in suitable SAR imagery, and compare those observations with historical AIS and protected areas.
2. Coastal monitoring: process repeated camera frames and AIS messages to maintain tracks and investigate motion over time. Begin with synchronized recorded datasets; connect a real camera when available.

Satellite acquisitions are intermittent. They are useful for wide-area and historical evidence, but they cannot supply a continuous video track. Coastal cameras and recorded video are the path for continuous tracking. A drone is an optional additional camera for local inspection after the core software is reliable; physical drone control, autonomous flight, and aviation compliance are outside the initial software scope.

The first delivery is an integrated, testable prototype. Coding can be accelerated, but dataset access, GPU availability, training duration, and independent evaluation still determine when research claims are justified. Execute the stages below by acceptance criteria rather than by calendar week. The implementation order starts with source truth and persistence before model fine-tuning, because retraining cannot fix incorrect timestamps, misleading provider semantics, discarded observations, or unstable review state.

## 1a. Plan review (October 2, 2026)

The plan was checked against the repository and primary sources. These corrections
have been applied in the sections noted; the first two change what the plan
depends on.

| # | Finding | Effect | Where fixed |
|---|---|---|---|
| 1 | The plan assumed Google Cloud hosting (Cloud Run, Cloud SQL, GCS, Cloud Run Jobs). The project is not deploying to Google Cloud | Hosting, storage, scheduling and CI sections were provider-specific | Sections 3, 13, 14 now name capabilities (container host, PostGIS, object storage, scheduler) rather than a vendor; section 1b adds a self-hosted path |
| 2 | Step 7 trained on HRSID/SSDD and tested on xView3. HRSID is 0.5-3 m imagery and live Sentinel-1 is 10 m pixels with 20x22 m resolution, so the plan repeated the mismatch it was meant to fix | Training would be validated on the wrong domain | Section 8: Sentinel-1-native training first, HRSID as pretraining and regression check; details in [small-vessel-detection-plan.md](small-vessel-detection-plan.md) |
| 3 | Step 6 said to "standardise SAR inputs" but did not name that three different intensity mappings already exist (`ml/pipeline/tiling.py` dB `[-50,0]`; `yolo-service` linear `2.5*VV`; undocumented HRSID conversions) | The most likely cause of poor transfer was untracked | Section 8 step 6 now names them and requires one shared, versioned function |
| 4 | No stage for provider-version changes. GFW announced pipeline v5 becomes the `latest` alias on 21 October 2026 and the code hard-coded `latest` | Live data could change under the system without trace | New Stage A2; configurable `GFW_SAR_DATASET`, resolved version stored per record; [gfw-v5-migration.md](gfw-v5-migration.md) |
| 5 | "Small-vessel recall" was a required metric (section 15) but undefined | The metric could not be computed or compared | Defined as recall per physical length bin with intervals; implemented in `ml/evaluation/detection_by_size.py` |
| 6 | Agents appeared only as "evidence-grounded explanations"; no tools for the live data model, no evaluation, no injection threat model, and the Ask agent's hand-written knowledge was out of date | Agents could contradict the system they describe | New section 12a and [agent-architecture-plan.md](agent-architecture-plan.md); knowledge corrected with drift tests |
| 7 | The local run path (`docker compose up`) did not produce a working app: wrong container ports, no `/api` proxy for the frontend, no live-feed variables, a briefing token default that reintroduced truncation | With no cloud host, this is the demo path | `docker-compose.yml` rewritten (syntax validated; images not built in the review environment) |
| 8 | No research positioning or literature basis in the plan | Weak case for the research claims | [literature-review.md](literature-review.md) with research questions RQ1-RQ5, mapped to stages in section 14 |
| 9 | The plan has no finalist-scope guidance, only acceptance-gated stages | A near-term demo needs a defined, honest subset | New section 17 |

Verified and left unchanged: the persistence, job-queue, association and
replay checkpoints in section 16 match the code and tests in the repository.

## 1b. Hosting without Google Cloud

The architecture needs five capabilities, none tied to one vendor:

| Capability | Requirement | Options |
|---|---|---|
| Container host | Runs the backend, frontend and YOLO service images | Local `docker compose`; any container platform or VM. Azure Container Apps fits if Azure is already used for training |
| Database | PostgreSQL with PostGIS | Local container, or a managed PostGIS-capable Postgres on any provider |
| Object storage | Immutable evidence and model artifacts, checksummed | Local volume for the demo; S3-compatible or Azure Blob storage when hosted |
| Scheduler/worker | Finite jobs for GFW refresh and processing | The existing database-backed job worker run by any scheduler (cron, a container job, a platform scheduler) |
| LLM | Gemini by API key, or Vertex if a project exists | `GEMINI_API_KEY` (already supported); no cloud project needed |

The GitHub Actions workflows under `.github/workflows/` deploy to Google Cloud Run.
They are legacy for this project: leaving them as push triggers will show failing
runs on every backend, frontend or YOLO change. Before a public review, either
restrict them to manual `workflow_dispatch` or replace them with a workflow for the
chosen host. For a time-boxed demo the most reliable option is local
`docker compose` plus the recorded-sequence replay, which removes cold starts and
provider outages from the critical path.

## 2. Current repository and intended modifications

The following structure was inspected locally while writing this plan. Hosted services were not checked in this documentation task.

| Existing component | Intended change |
|---|---|
| `frontend/`: React 18, TypeScript, Vite, Leaflet | Keep the dashboard; add source health, coverage, histories, replay, jobs, and evidence views |
| `backend/app/main.py`: FastAPI with startup background ingestion | Keep the API; move recurring ingestion and expensive processing to durable workers |
| `backend/app/services/gfw_ingest.py` | Preserve provider semantics, provenance, timestamps, and all valid records |
| `backend/app/services/ais_stream.py` | Introduce durable messages, history, time alignment, and availability states |
| `backend/app/services/sentinel_sar.py` | Record scene metadata and reuse a versioned SAR preprocessing contract |
| `backend/app/services/mpa_index.py` | Preserve spatial lookup; version boundaries and evaluate geographic accuracy |
| `backend/app/store/` | Migrate process/file state into PostgreSQL/PostGIS through a repository interface |
| `backend/app/api/routes/verify.py` | Make verification repeatable without accumulating risk; validate location and acquisition correspondence |
| `backend/app/agents/` | Generate explanations from retrieved evidence with source references |
| `yolo-service/` | Version model serving and preprocessing; return boxes and provenance separately from risk |
| `ml/` | Add dataset manifests, reproducible training, evaluations, tracking benchmarks, and model packaging |
| `.github/workflows/deploy-*.yml` | Retain separate service deployment; add tests, staging checks, migrations, and rollback gates |

The recorded baseline in `backend/data/metrics.json` is YOLO11n, 50 epochs, 2,857 training images and 715 validation images, mAP50 0.838, mAP50-95 0.579, precision 0.830, and recall 0.818. These are repository-recorded results, not reproduced results or current production accuracy. The listed 122 scene detections are a count, not an accuracy score.

## 3. Target architecture

```mermaid
flowchart TB
    Providers[Satellite imagery / GFW / AIS / geographic context]
    Camera[Recorded video or authorized coastal camera]
    Web[Vite analyst dashboard]
    API[FastAPI authenticated API]
    Jobs[Durable job records and task queue]
    Ingest[Provider ingestion workers]
    Vision[Image and video inference workers]
    Track[Tracking and AIS association]
    Rules[Context and alert evaluation]
    DB[(PostgreSQL + PostGIS)]
    Evidence[(GCS evidence and artifacts)]
    Explain[Evidence-grounded Gemini explanations]
    Train[Azure ML training and evaluation]
    Registry[Approved versioned model artifacts]

    Providers --> Ingest
    Camera --> Vision
    Web --> API
    API --> Jobs
    Jobs --> Ingest
    Jobs --> Vision
    Ingest --> DB
    Ingest --> Evidence
    Evidence --> Vision
    Vision --> DB
    Vision --> Track
    Ingest --> Track
    Track --> DB
    Track --> Rules
    Rules --> DB
    API --> DB
    API --> Explain
    DB --> Explain
    API --> Evidence
    Train --> Registry
    Registry --> Vision
```

Start with a modular backend and a few worker processes. Separate responsibilities through explicit contracts without creating a microservice for every module.

The project is not deploying to Google Cloud (see section 1b). A container host, PostGIS-capable Postgres, object storage, and a scheduler are required; see section 1b for vendor-neutral options. Azure supplies training compute. Export only approved, checksummed model artifacts to the deployment registry. Serving must not require Azure training jobs to stay running.

## 4. Plain-language system flow

This is how the upgraded system should behave from a user point of view.

1. The user selects a point, draws an area, or opens a monitored coastal site in the dashboard.
2. The frontend sends the selected geometry, time range, and requested mode to the FastAPI backend.
3. The backend checks which sources can answer that request: satellite catalog, existing SAR evidence, recorded or live camera frames, AIS history, MPA boundaries, and geofences.
4. If suitable satellite imagery exists, the SAR workflow processes the acquisition with the approved model. If coastal video exists, the video workflow detects vessels frame by frame and links detections into tracks.
5. The system matches each observation or track against AIS messages by time, location, motion, and uncertainty. It returns `matched`, `unmatched`, `ambiguous`, or `unavailable`; missing AIS is never treated as automatic proof that a transponder was deliberately disabled.
6. The spatial layer compares the observation or track with MPAs, exclusion zones, port areas, and other configured boundaries.
7. The rules layer creates alerts only when there is enough evidence, such as zone entry, unusual dwell, route deviation, status/motion inconsistency, or repeated missing association under usable AIS coverage.
8. The dashboard shows observations, tracks, source coverage, evidence chips, AIS candidates, MPA context, alert reasoning, and review status.
9. Gemini can explain the evidence in analyst-friendly language, but deterministic records and rules remain the source of truth.

The key idea: OceanGuard should not simply draw red dots. It should show what was observed, when it was observed, which source produced it, how confident the system is, what matching evidence exists, and what remains unknown.

### Satellite versus coastal tracking

Satellite SAR is best for wide-area detection and evidence snapshots. It can reveal vessel-like objects even when AIS is absent, and it can cover remote regions where no camera exists. Its limits are revisit time, acquisition availability, resolution, and scene conditions. A vessel can move far between satellite passes, so satellite observations are usually point-in-time evidence rather than a continuous track.

Coastal camera monitoring is best for continuous local tracking. It can maintain identity through frames, measure movement, and support stronger behavior analysis when calibration and timing are reliable. Its limits are field of view, weather, night conditions unless thermal exists, occlusion, camera placement, and calibration quality.

Drones should be treated as another camera source. They can help inspect a selected incident or collect extra evidence, but the first research contribution should not depend on autonomous drone control. Build the software so drone imagery can enter later through the same evidence, observation, and tracking contracts.

## 5. Source handling and data truth

Each provider adapter must return a source identifier, source record identifier, acquisition or observation time, ingestion time, geometry, units, quality information, and a reference to the original response or evidence.

- Keep GFW grid summaries in an `ActivityAggregate` layer. A grid count must not become a uniquely identified vessel or a model confidence value.
- Store observation-level provider detections only when the response actually contains observation-level evidence.
- Deduplicate by provider identity and acquisition provenance. Do not discard distinct vessels merely because they occupy the same geographic cell.
- Preserve missing timestamps as unknown. Never replace them with the current time and present the result as a fresh acquisition.
- Cluster and paginate for the map without deleting stored observations.
- Keep seed/demo data explicitly labeled and separate from operational observations.
- Preserve the last successful dataset during provider failure and mark its age.
- Record coverage as space, time, sensor, and availability. Global MPA polygons do not imply global vessel observations.

Provider health must distinguish configured, healthy, degraded, unauthorized, quota-limited, unavailable, and stale. A configured key alone proves no connectivity. Use bounded real requests, cache results, and redact credentials in diagnostics. Refresh OAuth tokens where supported; static token renewal can require account-owner action.

## 6. Persistent data model

Use database migrations and UTC timestamps. Store geometries with an explicit coordinate reference system; use appropriate metric/geodesic calculations for distance. Store large imagery and videos in object storage instead of database rows.

| Record | Main fields and purpose |
|---|---|
| `Source` | Provider, configuration reference, capabilities, status, last success, error category |
| `Acquisition` | Scene/video identifier, sensor, footprint, start/end time, resolution, evidence URI |
| `Observation` | Stable ID, source ID, acquisition ID, observed/ingested time, geometry or image box, uncertainty, model version |
| `ActivityAggregate` | Grid geometry, interval, count, measure, provider; never an individual vessel identity |
| `AISMessage` | MMSI as reported, message time, receive time, location, speed, course, heading, navigation status, quality |
| `Track` | Stable internal ID, sensor/domain, lifecycle state, first/last observation, optional identity hypothesis |
| `TrackPoint` | Track ID, timestamp, position or image coordinates, observed/predicted flag, uncertainty, observation reference |
| `Association` | Candidate tracks/observations, AIS reference, method version, score, decision, rejection reasons |
| `Zone` | Boundary, designation, effective dates, source/version, applicable rules if known |
| `Alert` | Rule/version, supporting evidence, interval, severity, uncertainty, deduplication key, review status |
| `Evidence` | Immutable object URI, checksum, acquisition metadata, preprocessing and model versions |
| `Review` | Analyst, decision, reason, timestamp, related alert, audit history |
| `Job` | Request, state, progress, idempotency key, attempts, result, failure category |
| `ModelVersion` | Artifact digest, dataset/split versions, preprocessing, metrics, approval state |

Database constraints enforce source deduplication and valid references. Reviews are appended rather than silently overwritten. Record processing versions so new models can reprocess evidence without destroying earlier results.

## 7. End-to-end user flows

### Select a point or area on the map

1. The browser sends a point plus radius, or a polygon, a time interval, and requested sensor mode.
2. The API validates geometry, authorization, area size, time range, and quota, then returns a job ID.
3. A worker checks provider coverage and catalog availability. No imagery produces a clear no-coverage result.
4. Reuse cached acquisitions or fetch suitable evidence. Preserve the actual capture time.
5. Apply versioned preprocessing and inference, merge overlapping tile results, and store observations.
6. Retrieve AIS around the acquisition time, evaluate candidate matches and uncertainty, and calculate spatial context.
7. The UI displays observations, coverage, acquisition age, evidence, association state, and any justified alerts.

Clicking the map does not request an instant new satellite photograph. It searches available observations for that place and time.

### Process a video or camera stream

1. Register the source with timestamps, frame rate, calibration, and available camera pose metadata.
2. Detect vessels in frames and track them within the sequence.
3. Store image-space tracks even when geographic calibration is unavailable.
4. Convert to world coordinates only when calibration and uncertainty support it.
5. Compare eligible tracks with time-aligned AIS, preserving ambiguous candidates.
6. Display synchronized video and map history. Mark extrapolated positions as predicted.

Camera pixels cannot become valid latitude/longitude simply from a bounding box. Fixed-camera geometry and moving-drone pose require different calibration methods.

### Review an alert

An analyst opens the alert, checks its timeline, imagery, AIS candidates, zone context, and uncertainty, then records a decision. An evidence export includes the relevant source times, IDs, model versions, and review history. Gemini may explain that evidence; deterministic logic owns identity decisions and alert rules.

## 8. Detection and fine-tuning plan

Yes, fine-tuning is planned. First reproduce a baseline and fix the input pipeline so training addresses a measured problem.

1. Inventory existing weights, configurations, source datasets, label formats, and training logs. Mark missing provenance explicitly.
2. Create versioned dataset manifests with checksums, permissions, sensor/resolution information, scene identifiers, and split membership.
3. Split by acquisition, location, capture session, or complete sequence. Prevent adjacent frames and overlapping scene tiles from leaking across splits.
4. Freeze the test set. Select parameters and thresholds only using training/validation data.
5. Reproduce the existing detector on its recoverable evaluation set; save raw predictions and failure examples.
6. Standardize SAR inputs: one shared, versioned preprocessing function used by training, the YOLO service, and the backend. Three distinct mappings already exist (`ml/pipeline/tiling.py` dB `[-50, 0]`; the yolo-service chip path linear `2.5*VV`; and undocumented HRSID conversion). All three must be unified before any fine-tuned weights can be compared meaningfully. See [small-vessel-detection-plan.md](small-vessel-detection-plan.md).
7. Measure the current model on held-out xView3 Sentinel-1 scenes first (run A0 in the small-vessel plan). This baseline determines whether retraining is needed. If the gap is large: fine-tune on xView3 as the primary training set with HRSID/SSDD as a pretraining and regression check. If the gap is small: the preprocessing fix alone may be sufficient. Do not retrain on HRSID alone and test on xView3 — that reproduces the resolution mismatch.
8. Train a separate optical camera/video detector using appropriate maritime datasets. Do not assume SAR weights directly solve RGB or thermal detection.
9. Compare the existing YOLO family baseline with a reproducible RT-DETR-family baseline under equal data and compute budgets.
10. Begin with small smoke runs; use a configurable maximum of 100 epochs and validation-based early stopping for full runs. Evaluate selected configurations across three seeds when budget permits.
11. Add targeted hard negatives such as waves, docks, land structures, and glare; measure performance by vessel size and environment.
12. Package the selected model together with preprocessing, class definitions, thresholds, evaluation artifacts, and a model card.

Initial dataset candidates: FVessel for synchronized camera/AIS experiments; ShipsMOT and Singapore Maritime Dataset for visual tracking/detection; SeaDronesSee for aerial robustness; HRSID/SSDD/xView3 for SAR; NOAA/Danish AIS for trajectory work. Verify availability, labels, and licenses before downloading. A public dataset does not automatically grant commercial redistribution rights.

Tracking motion models and assignment algorithms do not necessarily need fine-tuning. Train appearance embeddings only if evaluation shows an identity-association benefit. Defer learned anomaly models until reliable trajectories and credible labels exist. Gemini fine-tuning is not required for this architecture.

## 9. Azure training architecture

Proposed resources: Azure ML workspace, private Blob storage for permitted datasets/artifacts, a GPU compute cluster with bounded scaling, a container environment, experiment tracking, and identity-based storage access.

- Parameterize subscription, resource group, region, compute SKU, maximum nodes, and job budget. GPU quota and actual cost must be checked before job submission.
- Upload datasets once, retaining manifests and checksums; avoid repeated large cross-cloud transfers.
- Run preparation, baseline, training, evaluation, and packaging as separate restartable jobs.
- Save checkpoints, environment versions, seeds, configuration, predictions, metrics, and logs for every experiment.
- Limit concurrent jobs and runtime; scale training compute to zero when idle and configure budget alerts.
- Promote only models passing the evaluation gate; export approved artifacts to GCS or the application artifact pipeline with digest verification.

Required external inputs are Azure account access through supported authentication, GPU quota, an agreed spending limit, permitted datasets, and any required download approvals. Secrets belong in managed secret stores, never repository files or chat.

## 10. Tracking and association

Establish detector-plus-ByteTrack and detector-plus-BoT-SORT baselines on complete labeled video sequences. Give tracks stable internal IDs and explicit states: tentative, confirmed, predicted, lost, and ended. A recovered identity is a hypothesis until evidence supports the link.

For AIS association, align by observation time, constrain candidates using motion and positional uncertainty, and solve assignments across candidates rather than choosing the nearest point independently. Preserve alternatives and reasons for rejection. An MMSI is a reported identity, not independent proof of identity.

Use four public association states:

- `matched`: sufficient supporting evidence for the selected association.
- `unmatched`: usable coverage exists but no candidate meets the criteria.
- `ambiguous`: several candidates remain plausible.
- `unavailable`: insufficient AIS coverage, timing, or source availability.

Research extension: include observation age, source availability, clock/calibration error, and uncertainty in assignment and recovery. Permit abstention. Compare against baseline association methods with controlled outages and naturally missing observations. Satellite cross-acquisition identity needs its own experiment and must not inherit video tracking claims.

## 11. Context and behavior intelligence

Start with versioned explainable rules: zone entry, sustained dwell, speed/course changes, route deviation, reported navigation-status inconsistency, and possible encounters. Require minimum duration and adequate observations; use hysteresis and deduplication to prevent repeated alert storms.

Keep detection confidence, identity confidence, behavioral evidence, and review priority as separate fields. MPA proximity alone does not establish fishing, authorization status, or an offence. Unknown rules and missing context must remain visible.

Verification must reference a specific acquisition, target location, model, and preprocessing version. Repeating the same verification returns the stored result and cannot repeatedly increase risk. Another vessel in a large image chip does not verify the selected target.

## 12. API contracts and dashboard

Proposed versioned endpoints, to be finalized through OpenAPI contracts:

| API | Purpose |
|---|---|
| `GET /v1/sources/health` | Provider availability, last success, age, and safe failure details |
| `GET /v1/coverage` | Spatial/temporal availability for a sensor and area |
| `GET /v1/observations` | Cursor-paginated observations filtered by area, time, and source |
| `GET /v1/activity` | Separate aggregate activity layer |
| `GET /v1/tracks` and `/v1/tracks/{id}` | Track summaries, history, and identity hypotheses |
| `GET /v1/alerts` | Filtered alerts and supporting evidence |
| `POST /v1/analysis-jobs` | Authorized point, area, or recorded-video analysis |
| `GET /v1/jobs/{id}` | Progress, result references, or failure |
| `POST /v1/alerts/{id}/reviews` | Audited analyst decision |
| `GET /v1/evidence/{id}` | Authorized metadata and short-lived media access |

Maintain compatibility for existing risk-event clients through a documented adapter while the dashboard migrates. Define which legacy fields cannot be populated truthfully and avoid inventing values to satisfy old UI expectations.

Dashboard work includes layer toggles for aggregates, observations, tracks, and MPAs; capture-time and stale-data badges; source-health details; map/video timeline replay; association explanations; job progress; analyst review; and mobile-friendly evidence panels. Use viewport queries and display clustering. Show empty, unavailable, loading, and failed states separately.

## 12a. Evidence-grounded agent architecture

The existing agents (Narrator, Briefing, Patrol, Ask) produce answers from hand-written knowledge and sample case fields alone. They have no tools for GFW activity cells, source health, associations, alerts, or tracks, and the Ask agent's system prompt drifted from the codebase twice. The full agent plan is in [agent-architecture-plan.md](agent-architecture-plan.md); key points for this plan:

1. **Agents describe; the system decides.** No agent changes a risk score, association state, review status, or threshold. Every agent has a deterministic fallback that works with no model key.
2. **Every factual statement cites a tool-result evidence id.** A mechanical verifier strips or flags unsupported numbers and ids after generation; if too little remains, the agent abstains. This prevents answers contradicting the displayed data.
3. **Ask v2** adds tools for activity cells, source health, associations, alerts, and tracks; replaces the hand-written knowledge with text generated from code constants and data files so it cannot drift. Drift is caught by `backend/tests/test_agent_knowledge.py`.
4. **Provenance sentinel (A2)** shows the requested and resolved GFW dataset version, data age, and sample-vs-live status in a banner. This is the minimal UI change needed before the final demo.
5. **Patrol planning**: OR-Tools for static, RL only as a simulation study reported as such.
6. **Evaluation**: ~100 labelled questions in four groups (answerable, unanswerable, ambiguous, adversarial); unsupported-claim rate, abstention precision/recall, and injection success rate. This is research question RQ5.
7. **Threat model**: vessel-name, destination, and provider description fields are attacker-influenceable; delimit them as data in prompts, cap lengths, and test with planted instructions.

Acceptance gates match the delivery order in [agent-architecture-plan.md](agent-architecture-plan.md) section 9.

## 13. Runtime, deployment, and operations

Run Vite/nginx and FastAPI in containers on any container host (local `docker compose` is the most reliable demo path; see section 1b for hosted options). Use PostgreSQL with PostGIS for durable state and S3-compatible or Azure Blob object storage for immutable evidence. The `.github/workflows/deploy-*.yml` files target Google Cloud Run and should be restricted to `workflow_dispatch` or replaced with a host-appropriate workflow before any public review. Begin with a durable task queue and scheduled finite ingestion jobs. Continuous AIS sockets and long-running video sessions need a supervised persistent worker or edge host; do not assume an ordinary request-driven API instance will maintain them reliably.

Use a database outbox or equivalent reliable handoff between committed records and processing tasks. Workers must tolerate duplicate delivery, resume from checkpoints, retry temporary failures with bounded backoff, and send exhausted jobs to a reviewable failure queue. Serialize provider calls where provider limits require it.

Use separate identities for deployment, API, workers, and training with scoped access. Public demo viewing can remain read-only. Protect mutation, upload, export, and expensive inference operations with authentication, roles, quotas, and input limits. Use secret references and short-lived federated CI credentials.

Deployment sequence: tests and container build; staging deployment; backward-compatible database migration; smoke test; representative inference test; application promotion; production smoke test. Retain previous application and model versions for rollback. Defer destructive schema cleanup until all clients have migrated.

Observe provider success/latency, ingestion lag, acquisition age, queue delay, inference latency, track loss, alert volume, database failures, and cost per job. Propagate a request/job identifier across logs. Configure backups and retention by data category, then test restoration rather than assuming backups work.

## 14. Implementation order and acceptance gates

| Stage | Deliverable | Required evidence before proceeding |
|---|---|---|
| A. Baseline audit | Reproducible local setup, provider inventory, known failures | Real bounded provider probes and documented failure categories; no claim that missing keys are necessarily expired |
| B. Truth corrections | Aggregates separated, stable provenance, AIS uncertainty, idempotent verification | Regression tests for unknown time, empty AIS, duplicate verification, and multiple vessels in one cell |
| C. Persistence | Migrations, PostGIS repositories, evidence storage, reviews | Restart and multiple-instance tests retain history and decisions; migration/restore test |
| D. Jobs and sources | Durable jobs, scheduled ingestion, retry, health and coverage | Duplicate-delivery, crash/restart, quota, and provider-failure tests |
| E. SAR workflow | Point/area request through acquisition, inference, and evidence UI | Known-scene integration test and explicit no-coverage behavior |
| F. Training pipeline | Azure ML job templates, dataset registry, reproduced baseline, candidate models | Stored artifacts, leakage checks, fixed test evaluation, budget controls; artifacts exported to a container-accessible artifact store (not GCS) |
| G. Tracking replay | Video ingestion, baseline trackers, timeline | HOTA/IDF1 and identity-switch results on held-out complete sequences |
| H. AIS fusion | Time alignment, candidate assignment, abstention, recovery | Association precision/coverage and outage-recovery evaluation |
| I. Alerts and review | Context rules, cases, grounded explanations | Event-level evaluation and human review traceability |
| J. Release | Dashboard integration, staging, deployment, rollback | Full user journey, authorization, load, restore, and production smoke checks |
| K. Research extension | Availability-aware method and benchmark | Ablations, equal-budget comparisons, confidence intervals, external test data |

Stages E and F can proceed in parallel once input contracts are fixed. Dashboard work can follow agreed API fixtures while backend stages run. Do not train on new labels until the split registry is frozen; do not implement learned behavior scoring before track quality is measured.

For each Codex task: inspect relevant source and repository instructions, describe the slice, implement it, run focused checks, update its documentation, and report verified outcomes. Publish only scoped changes when instructed. Avoid bundling every stage into one unreviewable commit.

## 15. Evaluation and completion criteria

- Detection: mAP50-95, precision/recall, small-vessel recall, false alarms per image or area, and performance by sensor/environment.
- Tracking: HOTA, IDF1, identity switches, fragmentation, and reacquisition delay.
- Association: correct assignment precision versus assignment coverage, ambiguity, abstention, and calibration.
- Alerts: event precision/recall, false alerts per vessel-hour, and analyst usefulness on labeled cases.
- Operations: latency, source lag, queue recovery, processing cost, and database/evidence durability.

Report results separately for clear/occluded targets, day/night where supported, small/large targets, normal/degraded input, and familiar/unseen locations. Use sequence- or scene-level confidence intervals. Synthetic outages supplement natural missing-data evaluation; they do not replace it.

Existing roadmap targets of 5-10 additional HOTA points, 20-40% fewer identity switches, and 20-30% fewer false alerts are hypotheses to test after baselines exist. Do not promise these gains or turn them into reported results.

The integrated prototype is complete when an analyst can select an area and time, understand available coverage, run analysis, inspect genuine evidence, replay supported tracks, see AIS uncertainty, review an alert, and retain that decision across deployments. Research readiness additionally requires reproducible datasets, baselines, ablations, and independent held-out evaluation. Live coastal readiness additionally requires a suitable real sensor feed and field validation.

## 16. Concrete first implementation slice

Start with source health, acquisition provenance, aggregate/observation separation, safe AIS states, and idempotent verification. These changes make existing results interpretable and prevent more training from hiding data-pipeline errors. Then add persistence and jobs before scaling ingestion or model training.

### First implementation checkpoint (September 25, 2026)

- GFW 4Wings report rows now enter a process-local `ActivityAggregate` snapshot with dataset, report interval, provider time when supplied, and ingestion time. `/activity/gfw` supports bbox filtering and pagination. The dashboard shows cyan activity cells separately from case records.
- `/ingest/status` reports process-local attempt/success times and sanitized failure categories. A failed refresh retains the last successful in-memory snapshot; a restart still loses it.
- The short AIS sample returns matched or ambiguous candidates only when message and observation times are close. An empty or unrelated sample is unavailable and cannot confirm deliberate AIS disabling.
- YOLO point scans no longer add to risk. The model service does not yet return a scene acquisition identifier or time, so a nearby model hit remains an unverified lead.
- The risk-event seed remains for demo cases. Persistent observation records, historical AIS, durable jobs, authentication, provider probes, and exact SAR scene provenance are still pending.

### Persistence checkpoint (September 25, 2026)

- A versioned PostGIS migration now defines spatial case and activity tables, append-only review history, and source snapshot state. `python -m app.store.migrate` applies it before database mode is enabled.
- When `DATABASE_URL` is supplied, the API selects PostgreSQL repositories for case records and GFW activity. Repeated identical GFW reports reuse a content-derived snapshot; changed reports retain separate snapshots. Review updates lock the case row and append a history record in one transaction.
- Local mode remains available for development. No Cloud SQL database, credentials, or live migration was supplied, so the database path still requires integration and restart tests against a dedicated instance. Persistent observations, tracks, evidence objects, durable jobs, and authenticated mutations remain for subsequent slices.

### Durable-job checkpoint (September 25, 2026)

- A second migration adds a database-backed GFW refresh queue with stable deduplication keys, leased claims, bounded retry delays, and a terminal state after exhausted attempts. Lease-token fencing prevents a prior worker from completing a reclaimed job.
- The finite worker command fetches one report and publishes the snapshot in the same transaction as job completion. Source failure retains the previous snapshot and records a sanitized failure category. Provider fetch and database storage failures remain distinct.
- This is queue infrastructure, not a deployed schedule. A dedicated PostGIS integration test is opt-in; Cloud SQL, Cloud Run Jobs/Scheduler, live credentials, and production operation still require setup and validation. The API startup/manual refresh path remains in place for compatibility until cutover.

### SAR provenance checkpoint (September 26, 2026)

- Point and area YOLO verification now validate coordinates and ISO request times before calling the inference service. Responses carry the requested center/time, provider, optional acquisition identifiers, and an explicit `coverage_status`.
- When the inference service does not return a scene ID and observed acquisition time, the API reports `scene_time_unverified`. This is intentional: a successful image response or model detection is not presented as proof of the exact satellite pass.
- The frontend displays this evidence state beside the model result. The result remains an observation candidate and does not establish vessel identity, AIS absence, or unauthorized activity. A future acquisition adapter must supply scene metadata before changing this state.

### Source-health checkpoint (September 26, 2026)

- GET /sources/status now presents one read-only readiness view for GFW activity, AISStream, Sentinel Hub, and the YOLO service. It reports configuration, recent activity state where available, sanitized error categories, and source limitations.
- Configured means credentials or a service URL are present; it does not mean the provider is reachable, authorized, current, or returning useful coverage. AIS remains sample_only, and Sentinel/YOLO remain on_demand until durable observation and acquisition records are implemented.

### Operational-record checkpoint (September 26, 2026)

- Migration 003 defines durable acquisitions, observations, evidence references, AIS messages, tracks, track points, associations, and deduplicated alerts with spatial and temporal indexes.
- A PostGIS operational repository and versioned read APIs now expose observations, track points, and alerts when DATABASE_URL is configured. Local demo mode returns an explicit database-not-configured response and does not convert sample risk events into fake tracks.
- Worker write adapters, authenticated mutation routes, GCS object storage, and live Cloud SQL validation remain pending. No tracking result or alert quality claim is implied by the schema alone.

### Association-policy checkpoint (September 26, 2026)

- A deterministic time-distance association service now produces auditable matched, unmatched, ambiguous, and unavailable decisions with method versions and rejection reasons.
- Alert generation is conservative and deduplicated: unavailable AIS creates no alert, while unmatched or ambiguous results create review candidates that explicitly avoid claiming illegal activity or deliberate AIS disabling.
- This is a rules baseline, not a trained tracker or behavior model. It must be evaluated against labeled sequences after observation and AIS ingestion workers are implemented.

### Dataset and tracking baseline checkpoint (September 26, 2026)

- `ml/datasets/splits.py` now creates deterministic, group-safe split manifests from JSON or JSONL records. A sequence, scene, or capture session remains entirely in one split, and the manifest records the seed, ratios, groups, and record ids. This prevents leakage before fine-tuning begins.
- `ml/pipeline/tracking.py` now provides a dependency-light nearest-neighbor constant-velocity baseline. It emits stable track ids, confirmed/tentative states, and short-gap predicted points so later HOTA, IDF1, identity-switch, and recovery experiments have a reproducible reference.
- The dataset archives are not yet fully collected, normalized, or licensed for redistribution. No detector has been fine-tuned with the new datasets, and the tracker has not been evaluated on labeled coastal sequences yet.

### Tracking evaluation checkpoint (September 26, 2026)

- `ml/evaluation/tracking_metrics.py` now provides a deterministic frame-level baseline for detection precision/recall, IDF1, identity switches, fragmentation, and match counts.
- The evaluator makes the center-distance matching threshold explicit and documents that official benchmark implementations must be used for final HOTA or publication results.
- No labeled coastal evaluation has been run yet. The remaining gate is to normalize a collected dataset into the split-manifest contract, then compare the baseline tracker against held-out sequences.

### Operational-ingest checkpoint (September 26, 2026)

- `backend/app/services/operational_ingest.py` now provides the worker-facing boundary for persisting an observation, its AIS messages, one association decision, and an optional review alert in deterministic order.
- Retry delivery is safe at the application layer because association and alert ids are derived from stable inputs and the PostGIS repository uses conflict-safe inserts. Database transactionality still depends on the future worker transaction wrapper and live integration test.
- The orchestration preserves `unavailable`, `unmatched`, and `ambiguous` as different states. It does not infer deliberate AIS disabling or create an alert when coverage is unavailable.

### Replay checkpoint (September 26, 2026)

- `ml/pipeline/replay.py` now replays timezone-aware recorded frames through the baseline tracker and writes JSON-ready track points.
- Replay rejects unordered or timezone-free frames and preserves the distinction between measured and predicted points. This is the input path for later held-out sequence evaluation; it does not create a live camera feed.

Related documents: [research roadmap](coastal-vessel-tracking-roadmap.md), [existing architecture](architecture.md), [SAR and map selection](live-sar-and-user-selection-flow.md), [training explanation](modules/model-training-and-evaluation.md), [literature review with RQ1-RQ5](literature-review.md), [GFW v5 migration runbook](gfw-v5-migration.md), [small-vessel detection plan](small-vessel-detection-plan.md), and [agent architecture plan](agent-architecture-plan.md).

## 17. Finalist demo scope

This section defines the honest, defensible scope for a near-term award final. Everything listed under **Show** is currently working or can be made working before 21 October 2026 without additional data downloads. Everything listed under **Do not claim** either has no measurement to back it or depends on stages not yet wired.

### Show

- **Live GFW activity layer** with pinned dataset version badge (`GFW_SAR_DATASET=public-global-sar-presence:v4.0`) and data-age timestamp. The version and age are reported by `/ingest/status` and visible in the provenance sentinel banner (A2).
- **Sample cases clearly labelled** as such: "122 detections from a single xView3 scene (2024-01-15); 4 seeded GFW examples." The KPI tile, legend, and data-info tooltip carry this label.
- **YOLO check as an unverified lead** — `coverage_status: scene_time_unverified` is shown beside any model result; the result is described as a model candidate, not a detection of a specific vessel.
- **Agents with cited evidence** — the Ask agent cites tool-result ids; the provenance sentinel shows data state; all agents have deterministic fallbacks.
- **GFW v4 vs v5 drift study (RQ1)** — run `app.tools.compare_gfw_versions` on two fixed historical windows over Bar Reef and a reference region before 21 October; present the cell-Jaccard, detection-ratio, and context breakdown as a research finding.
- **Small-vessel detectability measurement (RQ2)** — run the current `best.pt` on held-out xView3 scenes with `ml/evaluation/detection_by_size.py`; report size-binned recall and confidence intervals as the baseline before any retraining.
- **Write-route protection** — `ADMIN_API_KEY` set on any reachable deployment; `/ingest/status` reports `write_protected: true`.

### Do not claim

- Live dark-vessel scoring from the production pipeline (the score formula was removed from live ingestion on 25 September 2026; the only scored data are the 126 seed events).
- Sentinel-1 accuracy on live scenes (no such measurement exists yet; it is the Phase 2 target).
- Autonomy ("the system autonomously detects illegal fishing") — every agent result is advisory, bounded, and reviewer-triggered.
- "Every hull" or similar coverage claims.
- Association, alert, or tracking results from live data (Stages H, I not yet wired to production callers).
