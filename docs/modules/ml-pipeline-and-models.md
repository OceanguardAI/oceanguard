# ML Pipeline and Models Module

## 1. What this module is for

The `ml/` folder is the offline production line of the project.

Its job is to prepare and validate the artifacts that the live backend can use.

That includes:

- validating cached data and model files
- building `risk_events.json`
- syncing outputs into `backend/data/`
- checking whether the handoff state is healthy

This part of the repo is important even if the live demo is currently driven mostly by the backend's live GFW ingest path.

Why:

- the backend still relies on seed artifacts
- the ML workflow is the main reproducible offline path
- it defines the handoff contract between model work and runtime work

## 2. The ML folder structure

Main areas:

- `ml/README.md`
- `ml/run_full_ml_workflow.py`
- `ml/build_risk_events.py`
- `ml/pipeline/`
- `ml/validate_artifacts.py`
- `ml/validate_model.py`
- `ml/sync_outputs_to_backend.py`
- `ml/tests/`

Supporting folders:

- `ml/data/`
- `ml/models/`
- `ml/outputs/`
- `ml/Temprary/ml/`

The oddly named `Temprary/ml/` is currently used as a staging/cache source for materializing missing standard artifacts.

## 3. The main orchestration script

The main entrypoint is:

- `ml/run_full_ml_workflow.py`

This script is a workflow coordinator rather than a single algorithm file.

It performs:

1. optional artifact materialization
2. artifact inspection
3. optional model validation
4. event building
5. output writing
6. sync to backend handoff directory
7. workflow summary writing

This is a very useful pattern because it turns a set of scattered helper scripts into one reproducible pipeline entrypoint.

## 4. Why materialization exists

The repo expects a standard layout:

- `data/`
- `models/`
- `outputs/`

But real ML workflows often involve files coming from:

- Colab
- Drive
- another machine
- temporary staging folders

The materialization step lets the project recover the expected working layout from the temporary artifact cache.

This is a practical engineering decision, not a modeling decision.

## 5. The offline event-building role

The offline pipeline ultimately builds:

- `outputs/risk_events.json`

This file is important because it becomes:

- a backend seed dataset
- a reproducible handoff artifact

Even when live GFW data later replaces the store at runtime, the seed file still matters for:

- startup fallback
- offline development
- testability

## 6. The deterministic risk model in ML

`ml/pipeline/risk.py` contains the offline deterministic risk formula.

Current logic combines:

- detection confidence
- AIS match state
- AIS availability
- inside-MPA state
- near-MPA state
- image quality score
- optional fishing score
- optional repeated activity score

This gives a risk score and risk level.

Important note:

This formula is not exactly the same implementation as the live backend GFW ingest score.

That is a learning point worth remembering:

- the project has both an offline scoring path and a live operational scoring path
- they are related, but not identical

## 7. The pipeline submodules

The `ml/pipeline/` folder represents smaller responsibilities inside the offline flow.

### `tiling.py`

Used when raw SAR scenes need to be broken into model-friendly regions.

### `detect.py`

Runs object detection on prepared inputs.

### `georeference.py`

Maps model detections back into real-world coordinates.

### `enrich.py`

Adds contextual information to raw detections.

### `risk.py`

Turns enriched detections into scored operational events.

This split is good architecture because the work is conceptually staged:

- prepare
- detect
- map
- enrich
- score

## 8. Model validation

The project includes:

- `ml/validate_model.py`

This exists because "the file exists" is not enough for model readiness.

A healthy ML pipeline should confirm:

- the model file is present
- it loads successfully
- expected metadata or behavior is available

This is one of the simplest but most important forms of ML pipeline hardening.

## 9. Artifact validation

The project also includes:

- `ml/validate_artifacts.py`
- `ml/report_ml_status.py`

These scripts provide operational visibility into the offline workspace state.

They help answer questions like:

- Do we have the expected files?
- Are the outputs structurally valid?
- Did sync to backend occur correctly?
- Are hashes aligned between ML output and backend handoff?

This matters because ML repos often fail in the handoff stage, not in the modeling stage.

## 10. Sync to backend

`ml/sync_outputs_to_backend.py` is the bridge between offline ML and live backend runtime.

This is a crucial seam in the project.

Without it, the offline outputs would remain isolated artifacts.

With it, they become runtime seed data.

That makes the ML folder practically useful to the product.

## 11. Relationship to the YOLO service

The repo has two model-related worlds:

### Offline ML workflow in `ml/`

Purpose:

- prepare artifacts
- validate outputs
- build reusable handoff files

### Online inference in `yolo-service/`

Purpose:

- fetch fresh SAR chips
- run the trained model on demand
- return detections to the backend/UI

This is an important distinction:

- `ml/` is the artifact and workflow side
- `yolo-service/` is the runtime inference side

## 12. Testing

The `ml/tests/` folder contains the main offline verification suite.

These tests are important because they encode what the repo considers stable behavior.

Typical areas covered:

- build-risk-events behavior
- enrichment behavior
- inference workflow expectations
- artifact materialization
- optional import handling
- report generation
- spatial pipeline behavior
- backend sync

For learning purposes, the tests are often as valuable as the implementation files because they show:

- what inputs are expected
- what outputs are considered correct
- which invariants are important

## 13. If you want to modify this module

### Change workflow orchestration

Start with:

- `ml/run_full_ml_workflow.py`

### Change risk-event building

Start with:

- `ml/build_risk_events.py`
- `ml/pipeline/risk.py`
- `ml/pipeline/enrich.py`

### Change raw SAR inference flow

Start with:

- `ml/run_inference_from_tif.py`
- `ml/pipeline/tiling.py`
- `ml/pipeline/detect.py`
- `ml/pipeline/georeference.py`

### Change validation logic

Start with:

- `ml/validate_artifacts.py`
- `ml/validate_model.py`
- `ml/report_ml_status.py`

## 14. Bottom line

The ML folder is the reproducibility and handoff layer of OceanGuard.

It is not merely "training code."

It is the part of the repo that makes the project's model outputs inspectable, portable, and usable by the backend runtime.
