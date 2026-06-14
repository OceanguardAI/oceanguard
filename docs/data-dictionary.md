# OceanGuard AI — Data Dictionary

Every field in the `risk_event` object, plus the provenance of every data source.

---

## RiskEvent Schema

The `risk_event` is the spine of the application. The ML pipeline produces it; the API serves it; the frontend renders it; the agents consume it.

```jsonc
{
  "id": "bar-reef-003",
  "source": "GFW",
  "lat": 8.51,
  "lon": 79.68,
  "risk_score": 0.61,
  "risk_level": "HIGH",
  "sar_confidence": 0.70,
  "image_quality": "Good",
  "ais_matched": false,
  "ais_data_available": true,
  "matching_method": "Spatial 2km + 3hr time window",
  "inside_mpa": false,
  "near_mpa": true,
  "mpa_name": "Bar Reef Marine Sanctuary",
  "distance_to_mpa_km": 0.4,
  "distance_from_port_km": 33.1,
  "nearest_port": "Marina (OSM)",
  "timestamp": "2026-06-09T14:32:00Z",
  "review_status": "Pending",
  "why_flagged": "...",
  "uncertainty": "...",
  "confidence_threshold": 0.45,
  "recommended_action": "Human reviewer should verify scene and external context.",
  "thumbnail": null
}
```

---

## Field Definitions

| Field | Type | Source | Description |
|---|---|---|---|
| `id` | string | Generated | Unique event identifier. GFW events: `bar-reef-NNN`. YOLO_SAR events: `yolo-NNN`. |
| `source` | enum | Pipeline | `"GFW"` = from Global Fishing Watch dark-vessel API. `"YOLO_SAR"` = from our YOLO11n inference on xView3 scene. |
| `lat` | float | Georef / GFW | WGS84 decimal degrees, north positive. |
| `lon` | float | Georef / GFW | WGS84 decimal degrees, east positive. |
| `risk_score` | float 0–1 | `risk.py` | Weighted deterministic score. See Risk Engine section below. |
| `risk_level` | enum | `risk.py` | `LOW` (<0.35) / `MEDIUM` (0.35–0.55) / `HIGH` (0.55–0.75) / `CRITICAL` (≥0.75). |
| `sar_confidence` | float 0–1 | YOLO / GFW | Detection confidence from the underlying SAR model. GFW events use 0.70 as representative value. |
| `image_quality` | enum | Pipeline | `"Good"` / `"Degraded"` / `"Poor"`. Reflects SAR image quality at detection location. Degrades `effective_conf` in risk formula. |
| `ais_matched` | bool | `enrich.py` | Whether a matching AIS broadcast was found within 2 km / ±3 h of the detection. `false` = potential dark vessel. |
| `ais_data_available` | bool | Pipeline | Whether AIS coverage existed for this area and time. `false` = absence of data, not evidence of evasion. |
| `matching_method` | string | Hardcoded | Describes the AIS matching algorithm: "Spatial 2km + 3hr time window". |
| `inside_mpa` | bool | `enrich.py` | Point-in-polygon test against the WDPA Bar Reef polygon (shapely). |
| `near_mpa` | bool | `enrich.py` | Distance to MPA boundary ≤ 5 km. |
| `mpa_name` | string | WDPA | Name of the nearest MPA. "Bar Reef Marine Sanctuary" for all Bar Reef events. |
| `distance_to_mpa_km` | float | `enrich.py` | Geodesic distance in km from detection point to nearest MPA boundary. |
| `distance_from_port_km` | float | `enrich.py` | Geodesic distance in km to nearest OSM port/marina. |
| `nearest_port` | string | OSM | Name/type of nearest port. "Marina (OSM)" for the Bar Reef demo. |
| `timestamp` | ISO 8601 string | GFW / tile | UTC datetime of detection or SAR acquisition. |
| `review_status` | enum | API | `Pending` / `Confirmed Risk` / `False Positive` / `Resolved`. Updated via `POST /risk-events/{id}/review`. |
| `why_flagged` | string | Narrator agent | Plain-language explanation from Claude (or deterministic fallback) of why this was flagged. |
| `uncertainty` | string | Narrator agent | Honest statement of what is uncertain about this detection. Always present. |
| `confidence_threshold` | float | Config | The detection confidence threshold used (0.45). Shown for transparency. |
| `recommended_action` | string | Hardcoded | Always "Human reviewer should verify scene and external context." Never automated. |
| `thumbnail` | string or null | Optional | Path to a SAR image crop of the detection. Null in MVP. |

---

## Risk Engine Formula

```
effective_conf = detection_conf × image_quality_score

if not ais_data_available:
    ais_score = 0.3     ← neutral; absence of data ≠ guilt
else:
    ais_score = 0.0 if ais_matched else 1.0

mpa_score = 1.0 if inside_mpa else (0.6 if near_mpa else 0.0)

risk_score = (0.30 × effective_conf
            + 0.25 × ais_score
            + 0.25 × mpa_score
            + 0.10 × fishing_score
            + 0.10 × repeated_activity_score)

risk_level:
    CRITICAL  if risk_score ≥ 0.75
    HIGH      if risk_score ≥ 0.55
    MEDIUM    if risk_score ≥ 0.35
    LOW       otherwise
```

**Weight rationale:**

| Factor | Weight | Rationale |
|---|---|---|
| SAR detection confidence | 0.30 | Core signal — but degraded by image quality |
| AIS non-match | 0.25 | Strong indicator of dark-vessel behaviour |
| MPA proximity | 0.25 | Ecological stakes — near/inside an MPA is the primary concern |
| Fishing activity | 0.10 | Vessel behaviour patterns (future: AIS trajectory analysis) |
| Repeated activity | 0.10 | Historical presence at same location (future: time-series) |

**AIS matching rule:** spatial ≤ 2 km + time window ± 3 hours.
**Near-MPA threshold:** ≤ 5 km from MPA boundary.
**Confidence threshold:** 0.45 — tuned for recall (a missed dark vessel is worse than a false alarm).

**Worked example — bar-reef-003:**
- conf=0.70, ais_matched=False, ais_data_available=True, inside_mpa=False, near_mpa=True, image_quality=1.0
- `0.30×0.70 + 0.25×1.0 + 0.25×0.6 + 0 + 0 = 0.21 + 0.25 + 0.15 = 0.61 → HIGH`

---

## ModelMetrics Schema

```jsonc
{
  "model": "YOLO11n",
  "dataset": "HRSID (2857 train / 715 val)",
  "epochs": 50,
  "map50": 0.838,
  "map50_95": 0.579,
  "precision": 0.830,
  "recall": 0.818,
  "confidence_threshold": 0.45,
  "validation_scene": "xView3 590dd08f71056cacv",
  "detections_on_real_scene": 122,
  "training_history": [
    { "epoch": 1, "map50": 0.61, "loss": 1.80 },
    ...
    { "epoch": 50, "map50": 0.838, "loss": 0.55 }
  ]
}
```

---

## Data Sources & Provenance

### HRSID — Training Data
- **Full name:** High-Resolution SAR Images Dataset
- **URL:** https://github.com/chaozhong2010/HRSID
- **Contents:** 5604 SAR images, 16951 ship instance annotations, COCO format
- **Split used:** 2857 train / 715 val (80/20)
- **Sensor:** TerraSAR-X, Sentinel-1, GF-3 (multi-sensor)
- **How used:** Fine-tuned YOLO11n for 50 epochs, imgsz=640, T4 GPU, 1.69 hours

### xView3-SAR — Validation Scene
- **Full name:** xView3 Synthetic Aperture Radar Ship Detection Challenge Dataset
- **URL:** https://iuu.xview.us/
- **Paper:** https://arxiv.org/abs/2206.00897
- **Scene ID used:** `590dd08f71056cacv`
- **Location:** Gulf of Guinea, West Africa (UTM zone 31N / EPSG:32631)
- **Band used:** `VH_dB.tif` (cross-polarisation, better for vessel detection)
- **Dimensions:** 28676 × 24522 pixels at 10 m resolution
- **Geo-transform origin:** x = 477060.79 m, y = 793583.94 m (UTM)
- **Nodata value:** -32768
- **Tiling:** 640×640 px tiles, dB normalised [-50, 0] → [0, 255] uint8; 1174 tiles, 498 skipped (<50% valid)
- **Result:** 122 vessel detections, confidences up to 0.76, fully georeferenced to WGS84

### Global Fishing Watch — Dark Vessel Data
- **Dataset:** `public-global-sar-presence:latest`
- **Filter:** `matched='false'` (no AIS match — potential dark vessels)
- **Date range:** 2025-06-10 to 2026-06-09 (366-day max)
- **Bounding box:** Bar Reef area `[[79.55,8.45],[79.90,8.45],[79.90,8.80],[79.55,8.80],[79.55,8.45]]`
- **API:** https://globalfishingwatch.org/our-apis/documentation
- **Cached at:** `ml/data/gfw_bar_reef_sar_unmatched.json`
- **Result:** 4 unmatched SAR detections; one 0.4 km from Bar Reef boundary

### WDPA — MPA Boundary
- **Full name:** World Database on Protected Areas
- **URL:** https://www.protectedplanet.net/en/thematic-areas/wdpa
- **Source used:** Google Earth Engine WDPA layer — `WCMC/WDPA/current/polygons`
- **Feature:** "Bar Reef Marine Sanctuary" (exact name required in EE query)
- **Cached at:** `ml/data/bar_reef.geojson`
- **Polygon coordinates (lon, lat):**
  ```
  [[79.73550022, 8.26746323], [79.76349894, 8.32294782],
   [79.78222715, 8.53409068], [79.68343578, 8.53142862],
   [79.68286497, 8.26487243], [79.73550022, 8.26746323]]
  ```

### OpenStreetMap — Port Data
- **Source:** Overpass API (`https://overpass-api.de/api/interpreter`)
- **Query:** `node["leisure"="marina"]` near Bar Reef bounding box
- **Cached at:** `ml/data/overpass_bar_reef_ports.json`
- **Result:** 1 marina at (8.2155202, 79.7061466) — ~33 km from bar-reef-003

---

## GFW Detection Records (raw)

The 4 dark-vessel detections near Bar Reef, with computed distances:

| id | lat | lon | timestamp | dist to MPA | inside | near |
|---|---|---|---|---|---|---|
| bar-reef-001 | 8.66 | 79.75 | 2026-06-09T06:12:00Z | ~14.1 km | false | false |
| bar-reef-002 | 8.48 | 79.58 | 2026-06-09T10:44:00Z | ~11.5 km | false | false |
| bar-reef-003 | 8.51 | 79.68 | 2026-06-09T14:32:00Z | **0.4 km** | false | **true** |
| bar-reef-004 | 8.68 | 79.69 | 2026-06-09T18:05:00Z | ~16.5 km | false | false |

All detections: `ais_matched=false`, `ais_data_available=true`, `detection_conf=0.70`, `image_quality_score=1.0`.
