# OceanGuard AI ML Pipeline

This folder contains the full offline ML workflow for OceanGuard AI:

- validate cached artifacts
- optionally validate the trained YOLO model
- build `risk_events.json`
- sync ML outputs into `backend/data`
- audit the final handoff state

## Layout

```text
ml/
├── data/
├── models/
├── outputs/
├── pipeline/
├── Temprary/ml/
├── build_risk_events.py
├── materialize_temporary_artifacts.py
├── report_ml_status.py
├── run_full_ml_workflow.py
├── run_inference_from_tif.py
├── sync_outputs_to_backend.py
├── validate_artifacts.py
└── validate_model.py
```

`ml/Temprary/ml/` is treated as the temporary cache for artifacts copied from Colab, Drive, or another machine.

## Setup

```powershell
cd ml
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Standard ML Workflow

Run the full non-training pipeline:

```powershell
python run_full_ml_workflow.py
```

What this does:

- auto-materializes missing standard artifacts from `ml/Temprary/ml`
- validates cached inputs
- validates `models/best.pt` when present
- builds `outputs/risk_events.json`
- syncs `risk_events.json` and `bar_reef.geojson` into `backend/data`
- writes `outputs/ml_workflow_summary.json`

If you do not have `best.pt` yet, skip the model load:

```powershell
python run_full_ml_workflow.py --skip-model-check
```

## Audit Current ML State

Print a human-readable ML status summary:

```powershell
python report_ml_status.py
```

Print the same report as JSON:

```powershell
python report_ml_status.py --as-json
```

The report checks:

- artifact counts and resolved source root
- model presence and metadata
- `risk_events.json` counts and schema health
- `bar-reef-003` expected risk profile
- backend handoff file presence and hash matches

## Work Directly From Temporary Artifacts

Copy artifacts from the temporary cache into the standard layout:

```powershell
python materialize_temporary_artifacts.py --source-root .\Temprary\ml --target-root . --overwrite
```

Validate the artifact set:

```powershell
python validate_artifacts.py
```

Validate the trained YOLO weights:

```powershell
python validate_model.py --model-path .\models\best.pt
```

## Raw SAR Inference Workflow

Use this only when you have the original SAR `.tif` scene and want to regenerate `detections_scene1_georef.json`.

```powershell
python run_inference_from_tif.py `
  --tif-path D:\path\to\scene.tif `
  --model-path .\models\best.pt
```

This runs:

- `pipeline/tiling.py`
- `pipeline/detect.py`
- `pipeline/georeference.py`

and writes georeferenced detections into `ml/outputs/`.

## Build Risk Events Only

If detections already exist and you only want the final ML output:

```powershell
python build_risk_events.py
```

## Test Suite

Run the default ML tests:

```powershell
python -m pytest tests -q
```

Run the full ML suite from the virtualenv, including optional spatial dependency tests:

```powershell
.\.venv\Scripts\python -m pytest tests -q
```

## Expected Healthy State

A healthy end-to-end ML run should show:

- `outputs/risk_events.json` with `126` events
- `4` `GFW` events
- `122` `YOLO_SAR` events
- `bar-reef-003` with `risk_score=0.61`
- `bar-reef-003` with `risk_level=HIGH`
- matching hashes between `ml/outputs/risk_events.json` and `backend/data/risk_events.json`
