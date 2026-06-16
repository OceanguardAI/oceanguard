# OceanGuard AI — ML Process Explained

**Status: ✅ Working, verified end-to-end on 2026-06-16.** This document explains what the ML part does, how the pieces fit together, and how to run/verify it yourself.

---

## What the ML part is for

OceanGuard's whole pitch rests on two separate proofs, and the ML pipeline produces both of them as a single output file: `risk_events.json`.

| | Proof A — "the model works" | Proof B — "the product works" |
|---|---|---|
| **Source** | YOLO11n vessel-detection model run on a real Sentinel-1 SAR scene (xView3 scene `590dd08f71056cacv`, Gulf of Guinea) | Global Fishing Watch's cached SAR-derived dark-vessel detections near Bar Reef Marine Sanctuary, Sri Lanka |
| **What it proves** | The trained model can find ships in real satellite radar imagery — 122 detections, mAP50 0.838 | The product's actual use case: 4 real unmatched-AIS detections near a protected area, one of them (`bar-reef-003`) just 0.4 km from the boundary |
| **In `risk_events.json`** | 122 events, `source: "YOLO_SAR"` | 4 events, `source: "GFW"` |

The ML pipeline's job is to turn the raw cached artifacts (a trained model + 4 JSON/GeoJSON files) into one unified, scored, schema-consistent `risk_events.json` that the backend serves and the frontend renders. Nothing in the ML pipeline calls a live API at request time — everything is pre-computed offline, which keeps the demo deterministic and fast.

---

## The five-stage pipeline

```
┌──────────────┐   ┌─────────────┐   ┌────────────────┐   ┌─────────┐   ┌────────────┐
│ 1. Tiling     │ → │ 2. Detect   │ → │ 3. Georeference │ → │ 4. Enrich │ → │ 5. Risk     │
│ tiling.py     │   │ detect.py   │   │ georeference.py │   │ enrich.py │   │ risk.py     │
└──────────────┘   └─────────────┘   └────────────────┘   └─────────┘   └────────────┘
   slices the         runs YOLO11n      converts pixel       computes        weighted
   28676×24522px       over each tile    coords → lat/lon     distance to     deterministic
   SAR GeoTIFF into    (0.45 conf        using the scene's    MPA boundary    score + level
   640×640 tiles       threshold)        UTM transform         and nearest      (LOW/MED/
                                                                 port            HIGH/CRITICAL)
```

**Stages 1-3 (tiling → detect → georeference) only run if you have the raw `.tif` scene and want to regenerate detections from scratch.** For the demo, this was already done once (via Colab) and the result is cached as `ml/outputs/detections_scene1_georef.json` — 122 detections with `lat`/`lon` already attached. You normally skip straight to stage 4.

**Stages 4-5 (enrich → risk) run every time** — they're cheap, pure-Python, and operate on both the cached YOLO detections and the cached GFW detections.

### Stage 1 — `pipeline/tiling.py`
Reads the SAR GeoTIFF with `rasterio` using windowed reads (never loads the full 700MB+ image into RAM). Each 640×640 window is normalised from dB radar values to an 8-bit grayscale PNG. Windows that are mostly `nodata` (less than 50% valid pixels) are skipped — this is why the real run produced 1174 tiles instead of the theoretical ~1672 (28676/640 × 24522/640).

### Stage 2 — `pipeline/detect.py`
Loads the YOLO11n model once (`ml/models/best.pt`, 5.5MB, single class "ship") and runs inference over tiles in chunks of 25, with a JSON checkpoint after each chunk so a crashed run can resume without re-processing tiles. Each detection record carries the tile it came from (`tile`), its pixel offset within that tile, and a confidence score.

### Stage 3 — `pipeline/georeference.py`
Converts each detection's tile-relative pixel coordinates into real-world latitude/longitude:
```
utm_x = scene_origin_x + (col_off + x_center_px) * pixel_size
utm_y = scene_origin_y - (row_off + y_center_px) * pixel_size
lon, lat = pyproj.Transformer(EPSG:32631 → EPSG:4326).transform(utm_x, utm_y)
```
`EPSG:32631` is the scene's UTM zone; `pixel_size` is 10m/pixel — both come from the scene's known geo-transform.

### Stage 4 — `pipeline/enrich.py`
For every detection (both GFW and YOLO), this computes:
- **Distance to the Bar Reef MPA boundary** (haversine great-circle distance to the nearest point on the WDPA polygon, or `0.0` if the point falls inside it)
- **`inside_mpa` / `near_mpa`** flags (`near` = within 5 km, not inside)
- **Distance to nearest port** (haversine to the nearest OSM marina/port node, or `(None, None)` if no port data exists — it no longer fabricates a fake distance)

There's a `shapely`-backed path for exact polygon geometry and a pure-Python fallback (ray-casting + planar projection) used when `shapely` isn't installed — both give the same classification for Bar Reef's polygon, with sub-100m differences in the exact distance number.

### Stage 5 — `pipeline/risk.py`
The deterministic, auditable scoring formula — this is the one piece of logic everything else in the product treats as ground truth:

```python
effective_conf = detection_conf * image_quality_score
ais_score = 0.3 if no AIS data available else (0.0 if AIS matched else 1.0)
mpa_score = 1.0 if inside_mpa else (0.6 if near_mpa else 0.0)

risk_score = (0.30 * effective_conf
            + 0.25 * ais_score
            + 0.25 * mpa_score
            + 0.10 * fishing_score          # reserved, currently always 0.0
            + 0.10 * repeated_activity_score) # reserved, currently always 0.0

risk_level = CRITICAL if risk_score >= 0.75
             HIGH     if risk_score >= 0.55
             MEDIUM   if risk_score >= 0.35
             LOW      otherwise
```

Why this design: SAR detects every vessel regardless of AIS status. A vessel with **no AIS match** near a **protected area** is the system's core signal — that's the 50% of the score (`ais_score` + `mpa_score`) doing the real work. `fishing_score`/`repeated_activity_score` are wired into the formula but not yet fed real data (always `0.0` today) — they're reserved for future GFW fishing-effort/repeat-visit signals.

**Worked example — `bar-reef-003`, the headline detection:**
```
detection_conf=0.70, ais_matched=False, ais_data_available=True,
inside_mpa=False, near_mpa=True, image_quality_score=1.0

risk_score = 0.30×0.70 + 0.25×1.0 + 0.25×0.6 + 0 + 0
           = 0.21 + 0.25 + 0.15 = 0.61 → HIGH
```

---

## The orchestration scripts (how it's actually run)

You don't call the 5 pipeline stages by hand — a few top-level scripts in `ml/` wire everything together:

| Script | What it does |
|---|---|
| `run_full_ml_workflow.py` | **The main entry point.** Materializes missing artifacts from the temp cache if needed → validates cached inputs → validates `best.pt` (skippable) → builds `risk_events.json` → syncs it + `bar_reef.geojson` into `backend/data/` → writes `ml/outputs/ml_workflow_summary.json`. This is the one command to run the whole ML side. |
| `build_risk_events.py` | The core transform: reads the 4 GFW detections + 122 cached YOLO detections, runs each through `enrich.py` + `risk.py`, and writes the unified 126-event `risk_events.json` with all 24 schema fields. Importable as a library (`build_events()`) or runnable standalone. |
| `materialize_temporary_artifacts.py` | Copies artifacts from `ml/Temprary/ml/` (the landing zone for files dropped in from Colab/Drive) into the standard `ml/data/`, `ml/models/`, `ml/outputs/` layout. |
| `validate_artifacts.py` | Sanity-checks the 4 cached data files exist and parse correctly — counts GFW/port/YOLO records, reports GeoJSON type, flags if GFW parsing had to fall back to canonical demo values. |
| `validate_model.py` | Loads `best.pt` and reports its class names, task type, and file size — confirms the model file isn't corrupted before anything depends on it. |
| `sync_outputs_to_backend.py` | Copies `ml/outputs/risk_events.json` and `ml/data/bar_reef.geojson` into `backend/data/`, so the backend always serves what the ML pipeline most recently produced. |
| `report_ml_status.py` | A read-only health check — prints (or `--as-json` dumps) artifact counts, model info, `risk_events.json` schema/count health, the `bar-reef-003` expected risk profile, and whether the backend's copy matches the ML output by content hash. **Run this any time you want to know "is the ML part actually working right now?"** |
| `run_inference_from_tif.py` | Only needed if you have the raw SAR `.tif` and want to regenerate `detections_scene1_georef.json` from scratch (runs stages 1-3). Not needed for the demo — the cached detections file already exists. |

### Standard workflow
```powershell
cd ml
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

python run_full_ml_workflow.py          # full pipeline, with model check
# or, if best.pt isn't available yet:
python run_full_ml_workflow.py --skip-model-check
```

### Just checking health, no changes
```powershell
python report_ml_status.py
```

---

## Verified working end-to-end (2026-06-16)

Ran `python run_full_ml_workflow.py` fresh:
```
Loading GFW data...
  Found 4 GFW detections
  bar-reef-001: dist=14.1km, near=False, score=0.46, level=MEDIUM
  bar-reef-002: dist=11.4km, near=False, score=0.46, level=MEDIUM
  bar-reef-003: dist=0.4km,  near=True,  score=0.61, level=HIGH
  bar-reef-004: dist=16.5km, near=False, score=0.46, level=MEDIUM

Loading YOLO_SAR detections...
  Found 122 YOLO detections

Total events: 126
GFW events: 4
YOLO events: 122
GFW fallback data used: False
bar-reef-003: 0.61 / HIGH / 2026-06-09T14:32:00Z
```

Then `python report_ml_status.py`:
```
Artifacts: GFW=4, YOLO=122, ports=1
Model: DetectionModel / detect / 1 classes
risk_events.json: 126 events / sources={'GFW': 4, 'YOLO_SAR': 122}
bar-reef-003: 0.61 / HIGH / near=True / inside=False
GFW fallback data used during build: False
Backend handoff: risk_events=True / bar_reef_geojson=True
Backend risk_events matches ML output: True
Backend bar_reef.geojson matches source: True
```

And `python -m pytest tests -q`:
```
20 passed, 2 skipped
```
(The 2 skips are `pyproj`/`rasterio`-dependent tests for the georeferencing math and tiling logic — those packages aren't installed in this environment. The tests themselves are written and will run wherever those optional deps are present; see `CODE_REVIEW_FINDINGS.md` for the test-coverage discussion.)

**Conclusion: the ML part is fully working.** Real GFW data parses correctly (no fallback triggered), the risk formula produces the exact documented headline number for `bar-reef-003`, and the backend's copy of the data is confirmed byte-identical to what the ML pipeline just produced.

---

## Where to look if something breaks

| Symptom | Likely cause | Where to check |
|---|---|---|
| `GFW fallback data used: True` | The real `gfw_bar_reef_sar_unmatched.json` doesn't match any recognised shape | `extract_gfw_entries()` in `build_risk_events.py` — print the raw JSON's top-level keys |
| `bar-reef-003` score isn't `0.61`/`HIGH` | MPA polygon or distance calc changed | `pipeline/enrich.py` (`distance_to_mpa`, `classify_mpa`) or `pipeline/risk.py` |
| `Backend risk_events matches ML output: False` | Backend's copy is stale | Run `python sync_outputs_to_backend.py` (or just re-run `run_full_ml_workflow.py`) |
| `FileNotFoundError` on a data file | An artifact wasn't placed/materialized | `python materialize_temporary_artifacts.py --source-root .\Temprary\ml --target-root . --overwrite`, then `python validate_artifacts.py` |
| Model load fails | `best.pt` missing or corrupted | `python validate_model.py --model-path .\models\best.pt` |
