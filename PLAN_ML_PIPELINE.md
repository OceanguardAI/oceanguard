# OceanGuard AI — ML Pipeline Team Plan (Team 3)

> **Your job:** Turn raw cached API files + the trained YOLO model into `risk_events.json`. The backend team depends entirely on this file. Do not change the risk formula. Do not restructure the output schema. Every field must be present.

---

## What You Deliver

```
ml/outputs/risk_events.json    ← 126 events (4 GFW + 122 YOLO_SAR)
```

After generating it, copy two files to the backend team's folder:
```bash
cp ml/outputs/risk_events.json  backend/data/risk_events.json
cp ml/data/bar_reef.geojson     backend/data/bar_reef.geojson
```

---

## Files You Own

```
ml/
├── requirements.txt
├── models/
│   └── best.pt                          ← place here from Colab/Drive
├── data/
│   ├── bar_reef.geojson                 ← place here from Colab/Drive
│   ├── gfw_bar_reef_sar_unmatched.json  ← place here from Colab/Drive
│   └── overpass_bar_reef_ports.json     ← place here from Colab/Drive
├── outputs/
│   ├── detections_scene1_georef.json    ← place here from Colab/Drive
│   └── risk_events.json                 ← YOU GENERATE THIS
├── pipeline/
│   ├── __init__.py                      ← empty file, required
│   ├── tiling.py                        ← implement
│   ├── detect.py                        ← implement
│   ├── georeference.py                  ← implement
│   ├── enrich.py                        ← implement
│   └── risk.py                          ← ALREADY WRITTEN, do not touch
└── build_risk_events.py                 ← implement (main script)
```

---

## Environment Setup

```bash
cd ml
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt`:
```
ultralytics>=8.0.0
rasterio>=1.3.0
pyproj>=3.5.0
shapely>=2.0.0
numpy>=1.24.0
pillow>=10.0.0
pytest>=7.0.0
```

Verify install:
```bash
python -c "import ultralytics, rasterio, pyproj, shapely; print('all OK')"
```

---

## Step 1 — Place Artifact Files

Get from Google Colab / Google Drive before doing anything else.

| File | Colab/Drive path | Destination |
|---|---|---|
| `best.pt` | `/content/drive/MyDrive/OceanGuard/models/hrsid_yolo11n-2/weights/best.pt` | `ml/models/best.pt` |
| `bar_reef.geojson` | `/content/drive/MyDrive/OceanGuard/datasets/wdpa/bar_reef.geojson` | `ml/data/bar_reef.geojson` |
| `gfw_bar_reef_sar_unmatched.json` | `/content/drive/MyDrive/OceanGuard/api_cache/gfw_bar_reef_sar_unmatched.json` | `ml/data/gfw_bar_reef_sar_unmatched.json` |
| `overpass_bar_reef_ports.json` | `/content/drive/MyDrive/OceanGuard/api_cache/overpass_bar_reef_ports.json` | `ml/data/overpass_bar_reef_ports.json` |
| `detections_scene1_georef.json` | `/content/drive/MyDrive/OceanGuard/datasets/xview3_scenes/detections_scene1_georef.json` | `ml/outputs/detections_scene1_georef.json` |

Verify files exist:
```bash
python -c "
import os
files = [
    'models/best.pt',
    'data/bar_reef.geojson',
    'data/gfw_bar_reef_sar_unmatched.json',
    'data/overpass_bar_reef_ports.json',
    'outputs/detections_scene1_georef.json',
]
for f in files:
    status = 'OK' if os.path.exists(f) else 'MISSING'
    print(f'{status}: {f}')
"
```

---

## Step 2 — Understand the Input File Formats

You need to know exactly what each JSON file looks like before parsing it.

### `gfw_bar_reef_sar_unmatched.json` — GFW API response

This is a GFW API JSON response. The structure looks like this:

```json
{
  "entries": [
    {
      "lat": 8.66,
      "lon": 79.75,
      "timestamp": "2026-06-09T06:12:00Z",
      "score": 0.92,
      "matched": false
    },
    {
      "lat": 8.48,
      "lon": 79.58,
      "timestamp": "2026-06-09T10:44:00Z",
      "score": 0.87,
      "matched": false
    },
    {
      "lat": 8.51,
      "lon": 79.68,
      "timestamp": "2026-06-09T14:32:00Z",
      "score": 0.95,
      "matched": false
    },
    {
      "lat": 8.68,
      "lon": 79.69,
      "timestamp": "2026-06-09T18:05:00Z",
      "score": 0.78,
      "matched": false
    }
  ]
}
```

> **Note:** The exact GFW JSON structure depends on which API endpoint was used. If the actual file has a different top-level key (e.g. `"results"` or the array is at the root), adjust your parser. Always `print(list(data.keys()))` first to inspect. The 4 detections and their lat/lon/timestamp values are canonical — those are real and correct regardless of structure.

The **canonical 4 detections** you must produce (regardless of how you parse the file):

| id | lat | lon | timestamp |
|---|---|---|---|
| bar-reef-001 | 8.66 | 79.75 | 2026-06-09T06:12:00Z |
| bar-reef-002 | 8.48 | 79.58 | 2026-06-09T10:44:00Z |
| bar-reef-003 | 8.51 | 79.68 | 2026-06-09T14:32:00Z |
| bar-reef-004 | 8.68 | 79.69 | 2026-06-09T18:05:00Z |

If the file cannot be parsed for any reason, **hardcode these 4 values** — they are from the real GFW data pull and are correct.

### `overpass_bar_reef_ports.json` — Overpass API response

Standard Overpass JSON format:

```json
{
  "version": 0.6,
  "elements": [
    {
      "type": "node",
      "id": 123456789,
      "lat": 8.2155202,
      "lon": 79.7061466,
      "tags": {
        "leisure": "marina",
        "name": "Marina"
      }
    }
  ]
}
```

Parse: `data["elements"]` → list of nodes with `lat`, `lon`, `tags`.

Port name: try `tags.get("name", tags.get("leisure", "Port (OSM)"))`.

### `bar_reef.geojson` — WDPA MPA polygon

Standard GeoJSON:

```json
{
  "type": "Feature",
  "properties": {
    "NAME": "Bar Reef Marine Sanctuary",
    "WDPAID": 4783
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [79.73550022, 8.26746323],
        [79.76349894, 8.32294782],
        [79.78222715, 8.53409068],
        [79.68343578, 8.53142862],
        [79.68286497, 8.26487243],
        [79.73550022, 8.26746323]
      ]
    ]
  }
}
```

Note: coordinates are `[longitude, latitude]` in GeoJSON (lon first). Shapely `shape()` handles this correctly.

### `detections_scene1_georef.json` — 122 YOLO detections

```json
[
  {
    "tile_path": "tiles/tile_r0000_c0000.png",
    "row_off": 0,
    "col_off": 0,
    "x_center_px": 312.4,
    "y_center_px": 198.7,
    "width_px": 45.2,
    "height_px": 22.8,
    "confidence": 0.76,
    "class_id": 0,
    "lat": 7.234567,
    "lon": 4.567890
  },
  ...
]
```

122 items total. Already has `lat` and `lon` (pre-georeferenced). You can load these directly without running georeference.py on them.

---

## Step 3 — Implement `pipeline/enrich.py`

Complete implementation:

```python
"""MPA distance, port distance, and spatial classification."""
from __future__ import annotations
import json
import math
from shapely.geometry import shape, Point
from shapely.ops import nearest_points


def load_mpa(geojson_path: str):
    """Load Bar Reef MPA polygon. Returns shapely geometry."""
    with open(geojson_path) as f:
        data = json.load(f)
    if data["type"] == "Feature":
        return shape(data["geometry"])
    elif data["type"] == "FeatureCollection":
        return shape(data["features"][0]["geometry"])
    else:
        return shape(data)  # bare geometry


def distance_to_mpa(lat: float, lon: float, mpa_polygon) -> float:
    """Geodesic distance in km from point to nearest MPA boundary.
    Returns 0.0 if the point is inside the MPA."""
    point = Point(lon, lat)  # shapely uses (lon, lat) = (x, y)
    if mpa_polygon.contains(point):
        return 0.0
    nearest = nearest_points(point, mpa_polygon.boundary)[1]
    return round(_haversine(lat, lon, nearest.y, nearest.x), 2)


def classify_mpa(distance_km: float) -> tuple[bool, bool]:
    """Return (inside_mpa, near_mpa).
    inside_mpa: distance == 0
    near_mpa:   distance > 0 and distance <= 5.0 km
    """
    inside = distance_km == 0.0
    near = (not inside) and distance_km <= 5.0
    return inside, near


def nearest_port_distance(lat: float, lon: float, ports_json_path: str) -> tuple[float, str]:
    """Return (distance_km, port_name) for the nearest OSM port."""
    with open(ports_json_path) as f:
        data = json.load(f)

    elements = data.get("elements", [])
    if not elements:
        # fallback: known marina coordinates
        return round(_haversine(lat, lon, 8.2155202, 79.7061466), 1), "Marina (OSM)"

    best_dist = float("inf")
    best_name = "Port (OSM)"
    for el in elements:
        if "lat" not in el or "lon" not in el:
            continue
        d = _haversine(lat, lon, el["lat"], el["lon"])
        if d < best_dist:
            best_dist = d
            tags = el.get("tags", {})
            best_name = tags.get("name", tags.get("leisure", "Port (OSM)"))

    return round(best_dist, 1), best_name


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


if __name__ == "__main__":
    mpa = load_mpa("data/bar_reef.geojson")
    # Test: bar-reef-003 should be ~0.4 km from MPA
    d = distance_to_mpa(8.51, 79.68, mpa)
    inside, near = classify_mpa(d)
    print(f"bar-reef-003: {d:.2f} km, inside={inside}, near={near}")
    assert near is True, f"Expected near=True, got {near}"
    # Test: bar-reef-001 should be ~14 km
    d2 = distance_to_mpa(8.66, 79.75, mpa)
    print(f"bar-reef-001: {d2:.2f} km")
    assert d2 > 5.0, f"Expected > 5km, got {d2}"
    print("enrich.py smoke test PASSED")
```

---

## Step 4 — `pipeline/risk.py` (ALREADY WRITTEN — DO NOT CHANGE)

This file is already implemented. Verify it gives the right answer:

```bash
python -c "
from pipeline.risk import calculate_risk
score, level = calculate_risk(
    detection_conf=0.70,
    ais_matched=False,
    ais_data_available=True,
    inside_mpa=False,
    near_mpa=True,
    image_quality_score=1.0,
)
print(f'score={score}, level={level}')
assert score == 0.61 and level == 'HIGH', f'WRONG: {score} {level}'
print('risk.py OK')
"
```

Expected: `score=0.61, level=HIGH`

---

## Step 5 — Implement `build_risk_events.py`

This is your main script. It reads all data files and writes `outputs/risk_events.json`.

### Complete implementation:

```python
"""Build risk_events.json from GFW dark-vessel data and YOLO xView3 detections."""
from __future__ import annotations
import json
import os
import sys

# Allow running from ml/ directory
sys.path.insert(0, os.path.dirname(__file__))

from pipeline.enrich import load_mpa, distance_to_mpa, classify_mpa, nearest_port_distance
from pipeline.risk import calculate_risk

DATA_DIR = "data"
OUTPUTS_DIR = "outputs"
os.makedirs(OUTPUTS_DIR, exist_ok=True)

MPA_NAME = "Bar Reef Marine Sanctuary"
MATCHING_METHOD = "Spatial 2km + 3hr time window"
CONFIDENCE_THRESHOLD = 0.45
RECOMMENDED_ACTION = "Human reviewer should verify scene and external context."

# ── Load shared resources ─────────────────────────────────────
mpa_polygon = load_mpa(os.path.join(DATA_DIR, "bar_reef.geojson"))
ports_json  = os.path.join(DATA_DIR, "overpass_bar_reef_ports.json")

events: list[dict] = []


# ── Part 1: GFW dark-vessel events ───────────────────────────
print("Loading GFW data...")
with open(os.path.join(DATA_DIR, "gfw_bar_reef_sar_unmatched.json")) as f:
    gfw_raw = json.load(f)

# Handle different possible GFW response structures
if isinstance(gfw_raw, list):
    gfw_entries = gfw_raw
elif "entries" in gfw_raw:
    gfw_entries = gfw_raw["entries"]
elif "results" in gfw_raw:
    gfw_entries = gfw_raw["results"]
elif "data" in gfw_raw:
    gfw_entries = gfw_raw["data"]
else:
    # Fallback: use canonical values from the real data pull
    print("  Warning: unrecognised GFW format, using canonical values")
    gfw_entries = [
        {"lat": 8.66, "lon": 79.75, "timestamp": "2026-06-09T06:12:00Z"},
        {"lat": 8.48, "lon": 79.58, "timestamp": "2026-06-09T10:44:00Z"},
        {"lat": 8.51, "lon": 79.68, "timestamp": "2026-06-09T14:32:00Z"},
        {"lat": 8.68, "lon": 79.69, "timestamp": "2026-06-09T18:05:00Z"},
    ]

print(f"  Found {len(gfw_entries)} GFW detections")

for i, entry in enumerate(gfw_entries, start=1):
    lat = float(entry["lat"])
    lon = float(entry["lon"])
    timestamp = entry.get("timestamp", "2026-06-09T12:00:00Z")
    event_id = f"bar-reef-{i:03d}"

    # Spatial enrichment
    dist_km = distance_to_mpa(lat, lon, mpa_polygon)
    inside, near = classify_mpa(dist_km)
    port_dist, port_name = nearest_port_distance(lat, lon, ports_json)

    # Risk scoring
    risk_score, risk_level = calculate_risk(
        detection_conf=0.70,
        ais_matched=False,
        ais_data_available=True,
        inside_mpa=inside,
        near_mpa=near,
        image_quality_score=1.0,
    )

    event = {
        "id": event_id,
        "source": "GFW",
        "lat": lat,
        "lon": lon,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "sar_confidence": 0.70,
        "image_quality": "Good",
        "ais_matched": False,
        "ais_data_available": True,
        "matching_method": MATCHING_METHOD,
        "inside_mpa": inside,
        "near_mpa": near,
        "mpa_name": MPA_NAME,
        "distance_to_mpa_km": dist_km,
        "distance_from_port_km": port_dist,
        "nearest_port": port_name,
        "timestamp": timestamp,
        "review_status": "Pending",
        "why_flagged": "",
        "uncertainty": "",
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "recommended_action": RECOMMENDED_ACTION,
        "thumbnail": None,
    }
    events.append(event)
    print(f"  {event_id}: lat={lat}, lon={lon}, dist={dist_km:.1f}km, "
          f"near={near}, score={risk_score}, level={risk_level}")


# ── Part 2: YOLO_SAR events (xView3 validation scene) ────────
print("\nLoading YOLO_SAR detections...")
with open(os.path.join(OUTPUTS_DIR, "detections_scene1_georef.json")) as f:
    yolo_detections = json.load(f)

print(f"  Found {len(yolo_detections)} YOLO detections")

for i, det in enumerate(yolo_detections):
    lat = det["lat"]
    lon = det["lon"]
    conf = det.get("confidence", 0.50)
    risk_score, risk_level = calculate_risk(
        detection_conf=conf,
        ais_matched=False,
        ais_data_available=False,   # No AIS coverage for Gulf of Guinea scene
        inside_mpa=False,
        near_mpa=False,
        image_quality_score=1.0,
    )

    event = {
        "id": f"yolo-{i+1:03d}",
        "source": "YOLO_SAR",
        "lat": lat,
        "lon": lon,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "sar_confidence": round(conf, 3),
        "image_quality": "Good",
        "ais_matched": False,
        "ais_data_available": False,
        "matching_method": MATCHING_METHOD,
        "inside_mpa": False,
        "near_mpa": False,
        "mpa_name": None,
        "distance_to_mpa_km": None,
        "distance_from_port_km": None,
        "nearest_port": None,
        "timestamp": "2024-01-15T00:00:00Z",   # xView3 scene approximate date
        "review_status": "Pending",
        "why_flagged": "",
        "uncertainty": "",
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "recommended_action": RECOMMENDED_ACTION,
        "thumbnail": None,
    }
    events.append(event)


# ── Write output ───────────────────────────────────────────────
out_path = os.path.join(OUTPUTS_DIR, "risk_events.json")
with open(out_path, "w") as f:
    json.dump(events, f, indent=2)

print(f"\nDone. {len(events)} events written to {out_path}")
print(f"  GFW events:      {sum(1 for e in events if e['source'] == 'GFW')}")
print(f"  YOLO_SAR events: {sum(1 for e in events if e['source'] == 'YOLO_SAR')}")

# Sanity check
bar003 = next((e for e in events if e["id"] == "bar-reef-003"), None)
if bar003:
    print(f"\nbar-reef-003 check:")
    print(f"  score={bar003['risk_score']}, level={bar003['risk_level']}")
    print(f"  near_mpa={bar003['near_mpa']}, dist={bar003['distance_to_mpa_km']}km")
    if bar003["risk_level"] != "HIGH":
        print("  WARNING: expected HIGH risk level for bar-reef-003")
```

---

## Step 6 — `pipeline/tiling.py` (only needed to re-run SAR inference)

You only need this if you want to re-run the full SAR pipeline on the raw `.tif` file. The `detections_scene1_georef.json` already exists from the Colab run, so **skip this for the demo**. Implement it for completeness.

```python
"""Tile a large SAR GeoTIFF into 640×640 uint8 PNGs for YOLO inference."""
from __future__ import annotations
import os
import numpy as np
from PIL import Image
import rasterio
from rasterio.windows import Window


def tile_sar(
    tif_path: str,
    output_dir: str,
    tile_size: int = 640,
    db_min: float = -50.0,
    db_max: float = 0.0,
    nodata: float = -32768,
    min_valid_frac: float = 0.50,
) -> list[tuple[int, int, str]]:
    """
    Returns list of (row_off, col_off, tile_path).
    Expected result on xView3 scene: 1174 tiles written, 498 skipped.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []
    skipped = 0

    with rasterio.open(tif_path) as src:
        width, height = src.width, src.height
        rows = range(0, height, tile_size)
        cols = range(0, width,  tile_size)

        for row_off in rows:
            for col_off in cols:
                # Clamp to image bounds
                h = min(tile_size, height - row_off)
                w = min(tile_size, width  - col_off)

                window = Window(col_off, row_off, w, h)
                data = src.read(1, window=window).astype(float)

                # Count valid pixels
                valid_mask = data != nodata
                valid_frac = valid_mask.sum() / data.size
                if valid_frac < min_valid_frac:
                    skipped += 1
                    continue

                # Replace nodata with db_min before normalising
                data[~valid_mask] = db_min

                # Normalise dB to uint8
                normed = np.clip(
                    (data - db_min) / (db_max - db_min) * 255, 0, 255
                ).astype(np.uint8)

                # Pad to tile_size if at edge
                if h < tile_size or w < tile_size:
                    padded = np.zeros((tile_size, tile_size), dtype=np.uint8)
                    padded[:h, :w] = normed
                    normed = padded

                tile_path = os.path.join(
                    output_dir, f"tile_r{row_off:04d}_c{col_off:04d}.png"
                )
                Image.fromarray(normed).save(tile_path)
                results.append((row_off, col_off, tile_path))

    print(f"Tiling complete: {len(results)} written, {skipped} skipped")
    return results


if __name__ == "__main__":
    import sys
    tif = sys.argv[1] if len(sys.argv) > 1 else "data/VH_dB.tif"
    tiles = tile_sar(tif, "tiles/")
    print(f"First tile: {tiles[0]}")
```

---

## Step 7 — `pipeline/detect.py` (only needed to re-run SAR inference)

Also only needed if re-running inference. Skip for demo — `detections_scene1_georef.json` already exists.

```python
"""Run YOLO11n inference over SAR tiles. Chunked + resumable."""
from __future__ import annotations
import json
import os
import torch
from pathlib import Path
from ultralytics import YOLO


def _parse_offsets(tile_path: str) -> tuple[int, int]:
    """Extract row_off, col_off from filename tile_rROWW_cCOLL.png."""
    name = Path(tile_path).stem          # e.g. tile_r0640_c1280
    parts = name.split("_")              # ['tile', 'r0640', 'c1280']
    row_off = int(parts[1][1:])          # strip 'r'
    col_off = int(parts[2][1:])          # strip 'c'
    return row_off, col_off


def detect_tiles(
    tile_dir: str,
    model_path: str,
    conf_threshold: float = 0.45,
    chunk_size: int = 25,
    checkpoint_path: str | None = None,
) -> list[dict]:
    """Return list of detection dicts. Resumable via checkpoint_path."""
    torch.set_num_threads(2)  # prevent memory overload on CPU

    model = YOLO(model_path)

    # Collect all tile paths
    all_tiles = sorted(
        str(p) for p in Path(tile_dir).glob("tile_r*.png")
    )

    # Resume: load existing checkpoint
    done: set[str] = set()
    detections: list[dict] = []
    if checkpoint_path and os.path.exists(checkpoint_path):
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        detections = checkpoint.get("detections", [])
        done = set(checkpoint.get("processed_tiles", []))
        print(f"Resuming: {len(done)} tiles already processed, "
              f"{len(detections)} detections so far")

    remaining = [t for t in all_tiles if t not in done]
    print(f"Tiles to process: {len(remaining)}")

    # Process in chunks
    for chunk_start in range(0, len(remaining), chunk_size):
        batch_paths = remaining[chunk_start : chunk_start + chunk_size]

        # Run inference — predict returns one Results object per image
        results = model.predict(
            source=batch_paths,
            conf=conf_threshold,
            verbose=False,
            device="cpu",
        )

        # CRITICAL: zip paths with results — never rely on r.path
        for tile_path, r in zip(batch_paths, results):
            row_off, col_off = _parse_offsets(tile_path)

            if r.boxes is None or len(r.boxes) == 0:
                done.add(tile_path)
                continue

            for box in r.boxes:
                xyxy = box.xyxy[0].tolist()    # [x1, y1, x2, y2]
                x_center = (xyxy[0] + xyxy[2]) / 2
                y_center = (xyxy[1] + xyxy[3]) / 2

                detections.append({
                    "tile_path":    tile_path,
                    "row_off":      row_off,
                    "col_off":      col_off,
                    "x_center_px":  round(x_center, 2),
                    "y_center_px":  round(y_center, 2),
                    "width_px":     round(xyxy[2] - xyxy[0], 2),
                    "height_px":    round(xyxy[3] - xyxy[1], 2),
                    "confidence":   round(float(box.conf[0]), 4),
                    "class_id":     int(box.cls[0]),
                })
            done.add(tile_path)

        # Save checkpoint after every chunk
        if checkpoint_path:
            with open(checkpoint_path, "w") as f:
                json.dump(
                    {"detections": detections,
                     "processed_tiles": list(done)},
                    f
                )
        print(f"  Chunk {chunk_start//chunk_size + 1}: "
              f"{len(batch_paths)} tiles, "
              f"{len(detections)} detections total")

    print(f"Detection complete: {len(detections)} detections")
    return detections


if __name__ == "__main__":
    dets = detect_tiles("tiles/", "models/best.pt",
                        checkpoint_path="outputs/detect_checkpoint.json")
    print(f"Total detections: {len(dets)}")
```

---

## Step 8 — `pipeline/georeference.py` (only needed to re-run SAR inference)

```python
"""Convert tile pixel coordinates to WGS84 lat/lon."""
from __future__ import annotations
from pyproj import Transformer


def georeference_detections(
    detections: list[dict],
    geo_transform_x: float = 477060.79,
    geo_transform_y: float = 793583.94,
    pixel_size: float = 10.0,
    src_crs: str = "EPSG:32631",
    dst_crs: str = "EPSG:4326",
) -> list[dict]:
    """
    Adds 'lat' and 'lon' to each detection dict. Returns updated list.

    Formula:
        utm_x = geo_transform_x + (col_off + x_center_px) * pixel_size
        utm_y = geo_transform_y - (row_off + y_center_px) * pixel_size
        lon, lat = transform(utm_x, utm_y)

    The xView3 scene (590dd08f71056cacv) is EPSG:32631 (UTM zone 31N).
    Origin: x=477060.79, y=793583.94 (upper-left corner of the image).
    Pixel size: 10 m.
    """
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)

    for det in detections:
        utm_x = geo_transform_x + (det["col_off"] + det["x_center_px"]) * pixel_size
        utm_y = geo_transform_y - (det["row_off"] + det["y_center_px"]) * pixel_size
        lon, lat = transformer.transform(utm_x, utm_y)
        det["lon"] = round(lon, 6)
        det["lat"] = round(lat, 6)

    return detections


if __name__ == "__main__":
    # Smoke test: a detection at tile origin should georef near scene origin
    test = [{"col_off": 0, "row_off": 0, "x_center_px": 0, "y_center_px": 0}]
    result = georeference_detections(test)
    print(f"Origin: lat={result[0]['lat']}, lon={result[0]['lon']}")
    # Should be approximately lat=7.17, lon=4.31 (Gulf of Guinea)
```

---

## Step 9 — Run Everything

```bash
cd ml

# Main script — generates risk_events.json
python build_risk_events.py
```

Expected console output:
```
Loading GFW data...
  Found 4 GFW detections
  bar-reef-001: lat=8.66, lon=79.75, dist=14.1km, near=False, score=0.46, level=MEDIUM
  bar-reef-002: lat=8.48, lon=79.58, dist=11.5km, near=False, score=0.46, level=MEDIUM
  bar-reef-003: lat=8.51, lon=79.68, dist=0.4km,  near=True,  score=0.61, level=HIGH
  bar-reef-004: lat=8.68, lon=79.69, dist=16.5km, near=False, score=0.46, level=MEDIUM

Loading YOLO_SAR detections...
  Found 122 YOLO detections

Done. 126 events written to outputs/risk_events.json
  GFW events:      4
  YOLO_SAR events: 122

bar-reef-003 check:
  score=0.61, level=HIGH
  near_mpa=True, dist=0.4km
```

---

## Step 10 — Copy Outputs to Backend

```bash
cp outputs/risk_events.json ../backend/data/risk_events.json
cp data/bar_reef.geojson    ../backend/data/bar_reef.geojson
```

Tell the backend team these files are ready.

---

## Verification Checklist

Before handing off, confirm all of these:

- [ ] `outputs/risk_events.json` exists and has 126 events
- [ ] `bar-reef-003` has `risk_score=0.61`, `risk_level="HIGH"`, `near_mpa=true`, `distance_to_mpa_km` ≈ 0.4
- [ ] `bar-reef-003` has `inside_mpa=false` (it is near, not inside)
- [ ] All 4 GFW events have `ais_matched=false`, `ais_data_available=true`
- [ ] All 122 YOLO events have `source="YOLO_SAR"`, `ais_data_available=false`
- [ ] No event has `None` for `risk_score` or `risk_level`
- [ ] Every event has all 23 fields present (check schema above)
- [ ] `backend/data/risk_events.json` is the same file
- [ ] `backend/data/bar_reef.geojson` is copied

Quick JSON validation:
```bash
python -c "
import json
with open('outputs/risk_events.json') as f:
    events = json.load(f)
print(f'Total events: {len(events)}')
gfw   = [e for e in events if e['source'] == 'GFW']
yolo  = [e for e in events if e['source'] == 'YOLO_SAR']
print(f'GFW: {len(gfw)}, YOLO_SAR: {len(yolo)}')
b3 = next(e for e in events if e['id'] == 'bar-reef-003')
print(f'bar-reef-003: score={b3[\"risk_score\"]}, level={b3[\"risk_level\"]}')
required = ['id','source','lat','lon','risk_score','risk_level',
            'sar_confidence','image_quality','ais_matched',
            'ais_data_available','matching_method','inside_mpa',
            'near_mpa','mpa_name','distance_to_mpa_km',
            'distance_from_port_km','nearest_port','timestamp',
            'review_status','why_flagged','uncertainty',
            'confidence_threshold','recommended_action','thumbnail']
for e in events[:5]:
    missing = [k for k in required if k not in e]
    if missing:
        print(f'MISSING fields in {e[\"id\"]}: {missing}')
print('Schema check done')
"
```

---

## Common Problems

| Problem | Cause | Fix |
|---|---|---|
| `shapely.errors.ShapelyError` | Wrong geometry type in geojson | Print `data["type"]` and adapt `load_mpa()` |
| `KeyError: 'elements'` | Overpass JSON has different structure | Print `list(data.keys())` and adjust |
| YOLO `CUDA error` | No GPU available | Add `device="cpu"` to `model.predict()` |
| `r.path` is wrong file | Ultralytics bug on batch predict | Always use `zip(batch_paths, results)` |
| `bar-reef-003` score not 0.61 | Distance calculation off | Check `near_mpa` threshold is exactly 5.0 km |
| 0 GFW detections | Wrong key in GFW JSON | Print raw JSON keys and adjust parser |

---

## What You Do NOT Own

- Do NOT touch `backend/` files
- Do NOT touch `frontend/` files
- Do NOT change the risk formula in `pipeline/risk.py`
- Do NOT change field names in the output schema — the backend expects exact field names
- Do NOT reorder events — just append GFW first, then YOLO_SAR
