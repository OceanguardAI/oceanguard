# OceanGuard AI — Data Dictionary

Every field in the `risk_event` object, plus the provenance of every data source.

---

## RiskEvent Schema

The `risk_event` is the spine of the application. The live ingestion pipeline produces it; the API serves it; the frontend renders it; the agents consume it.

```jsonc
{
  "id": "bar-reef-003",
  "source": "GFW",                        // "GFW" or "YOLO_SAR"
  "lat": 8.51,
  "lon": 79.68,
  "risk_score": 0.61,
  "risk_level": "HIGH",                   // LOW | MEDIUM | HIGH | CRITICAL
  "sar_confidence": 0.70,
  "image_quality": "Good",               // Good | Degraded | Poor
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
  "review_status": "Pending",            // Pending | Confirmed Risk | False Positive | Resolved
  "why_flagged": "...",                  // filled by narrator agent (Gemini) or deterministic fallback
  "uncertainty": "...",                  // always present
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
| `source` | enum | Pipeline | `"GFW"` = from Global Fishing Watch dark-vessel API. `"YOLO_SAR"` = from YOLO11n inference. |
| `lat` | float | GFW API / georef | WGS84 decimal degrees, north positive. |
| `lon` | float | GFW API / georef | WGS84 decimal degrees, east positive. |
| `risk_score` | float 0–1 | `gfw_ingest.py` (live) / `risk.py` (seed) | Deterministic score. See Risk Engine section below. |
| `risk_level` | enum | Risk engine | `LOW` (<0.45) / `MEDIUM` (0.45–0.60) / `HIGH` (0.60–0.80) / `CRITICAL` (≥0.80). |
| `sar_confidence` | float 0–1 | YOLO / GFW | Detection confidence from the underlying SAR model. |
| `image_quality` | enum | Pipeline | `"Good"` / `"Degraded"` / `"Poor"`. Degrades `effective_conf` in risk formula. |
| `ais_matched` | bool | GFW / AISStream | Whether a matching AIS broadcast was found within 2 km / ±3 h. `false` = potential dark vessel. |
| `ais_data_available` | bool | Pipeline | Whether AIS coverage existed for this area and time. `false` = absence of data, not evidence of evasion. |
| `matching_method` | string | GFW / system | Describes the AIS matching algorithm. GFW does server-side matching; annotated as `"GFW server-side AIS cross-match"`. |
| `inside_mpa` | bool | `mpa_index.py` | Point-in-polygon test against WDPA MPA polygons (Shapely STRtree). |
| `near_mpa` | bool | `mpa_index.py` | Distance to nearest MPA boundary ≤ 10 km (`NEAR_MPA_KM`). |
| `mpa_name` | string | WDPA | Name of the nearest MPA. |
| `distance_to_mpa_km` | float | `mpa_index.py` | Geodesic distance in km from detection point to nearest MPA boundary. |
| `distance_from_port_km` | float | `enrich.py` | Geodesic distance in km to nearest OSM port/marina. |
| `nearest_port` | string | OSM | Name/type of nearest port. |
| `timestamp` | ISO 8601 string | GFW / tile | UTC datetime of detection or SAR acquisition. |
| `review_status` | enum | API | `Pending` / `Confirmed Risk` / `False Positive` / `Resolved`. Updated via `POST /risk-events/{id}/review`. In-memory only (persist=False). |
| `why_flagged` | string | Narrator agent | Plain-language explanation from Gemini 2.5 Flash (or deterministic fallback) of why this was flagged. |
| `uncertainty` | string | Narrator agent | Honest statement of what is uncertain about this detection. Always present. |
| `confidence_threshold` | float | Config | The detection confidence threshold used (0.45). Shown for transparency. |
| `recommended_action` | string | Hardcoded | Always "Human reviewer should verify scene and external context." Never automated. |
| `thumbnail` | string or null | Optional | Base64 SAR chip PNG from YOLO verify result. Null until officer runs verification. |

---

## Risk Engine Formula

The **live** system scores detections additively as they are ingested from the
Global Fishing Watch SAR feed (`backend/app/services/gfw_ingest.py::_score_detection`).
Every term is transparent and explainable — there is no black box.

```
score = 0.25                      # baseline: any SAR vessel detection
      + 0.20  if not ais_matched  # no matching AIS identity — possible dark vessel
      + mpa_proximity_bonus:      # proximity to a protected area (largest factor)
            +0.45  if inside an MPA          (distance_to_mpa_km <= 0)
            +0.30  if within 10 km of one    (<= 10)
            +0.15  if within 50 km           (<= 50)
            +0.00  otherwise (open ocean)
      + 0.05  if detections > 1   # repeated presence at the same SAR cell

score = min(score, 0.99)          # capped; nothing is ever "certain"

risk_level:
    CRITICAL  if score >= 0.80
    HIGH      if score >= 0.60
    MEDIUM    if score >= 0.45
    LOW       otherwise
```

**Factor rationale:**

| Factor | Contribution | Rationale |
|---|---|---|
| SAR detection baseline | 0.25 | A confirmed radar vessel is the starting signal |
| No AIS identity | +0.20 | GFW could not match the hit to any AIS broadcast — the core dark-vessel signal |
| MPA proximity | up to +0.45 | Ecological stakes — inside/near an MPA is the primary concern; tiered by distance |
| Repeated presence | +0.05 | Multiple SAR detections at the same cell |

**Near-MPA threshold:** ≤ 10 km from the MPA boundary (`mpa_index.NEAR_MPA_KM`).
**Confidence threshold:** 0.45 — tuned for recall (a missed dark vessel is worse than a false alarm).
**YOLO agreement boost:** +0.10 to `risk_score` (capped at 0.99) when an officer's on-demand YOLO check independently confirms a GFW detection (`verify.py::_AGREEMENT_BOOST`).

**Worked example — a dark vessel inside an MPA:**
- `ais_matched=False`, `inside_mpa=True` (distance 0 km), single detection
- `0.25 + 0.20 + 0.45 = 0.90 → CRITICAL`
- If the same cell shows repeated detections: `0.90 + 0.05 = 0.95 → CRITICAL`

**Worked example — a dark vessel ~8 km from an MPA boundary:**
- `ais_matched=False`, `near_mpa=True` (≤ 10 km)
- `0.25 + 0.20 + 0.30 = 0.75 → HIGH`

> **Offline seed-data note:** The bundled `risk_events.json` fallback (used only
> when no `GFW_API_TOKEN` is configured) was generated by the offline ML pipeline
> (`ml/pipeline/risk.py`), which uses a more detailed weighted variant with a
> `bar-reef-NNN` id scheme. In any deployed environment with a GFW token, live
> ingestion replaces it and the additive formula above is authoritative.

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
    { "epoch": 1,  "map50": 0.61, "loss": 1.80 },
    { "epoch": 10, "map50": 0.72, "loss": 1.20 },
    { "epoch": 20, "map50": 0.78, "loss": 0.90 },
    { "epoch": 30, "map50": 0.81, "loss": 0.70 },
    { "epoch": 40, "map50": 0.83, "loss": 0.60 },
    { "epoch": 50, "map50": 0.838, "loss": 0.55 }
  ]
}
```

---

## Data Sources & Provenance

### HRSID — Training Data
- **Full name:** High-Resolution SAR Images Dataset
- **URL:** https://github.com/chaozhong2010/HRSID
- **Contents:** 5,604 SAR images, 16,951 ship instance annotations, COCO format
- **Split used:** 2,857 train / 715 val (80/20)
- **Sensor:** TerraSAR-X, Sentinel-1, GF-3 (multi-sensor)
- **How used:** Fine-tuned YOLO11n for 50 epochs, imgsz=640, T4 GPU, ~1.69 hours

### xView3-SAR — Validation Scene
- **Full name:** xView3 Synthetic Aperture Radar Ship Detection Challenge Dataset
- **URL:** https://iuu.xview.us/
- **Scene ID used:** `590dd08f71056cacv`
- **Location:** Gulf of Guinea, West Africa (UTM zone 31N / EPSG:32631)
- **Band used:** `VH_dB.tif` (cross-polarisation, better for vessel detection)
- **Dimensions:** 28,676 × 24,522 pixels at 10 m resolution
- **Tiling:** 640×640 px tiles, dB normalised [-50, 0] → [0, 255] uint8; 1,174 tiles
- **Result:** 122 vessel detections, confidences up to 0.76, fully georeferenced to WGS84

### Global Fishing Watch — Live Primary Detection Feed
- **Dataset:** `public-global-sar-presence:latest`
- **API:** https://globalfishingwatch.org/our-apis/documentation
- **What it provides:** SAR vessel detections with server-side AIS cross-matching. Entries with no vessel identity fields (empty MMSI/shipName) are dark detections.
- **Config:** `GFW_API_TOKEN`, `GFW_REGION_BBOX`, `GFW_LOOKBACK_DAYS` (default 7 days), `GFW_MAX_EVENTS` (default 600)
- **Auto-ingest:** `GFW_INGEST_ON_STARTUP=true` — runs at backend startup
- **Confidence threshold:** 0.45 applied during ingestion

### AISStream.io — Live AIS Cross-check
- **URL:** https://aisstream.io/
- **What it provides:** Real-time AIS vessel broadcast stream via WebSocket
- **How used:** `POST /ais/verify-dark` — confirms which SAR detections have no nearby AIS broadcast in real time
- **Config:** `AISSTREAM_API_KEY` in `backend/.env`

### WDPA — Marine Protected Area Boundaries
- **Full name:** World Database on Protected Areas
- **Provider:** UNEP-WCMC (United Nations Environment Programme World Conservation Monitoring Centre)
- **Source used:** Open ArcGIS REST endpoint — **no API token required**
- **How used:** `fetch_wdpa.py` downloads GeoJSON polygons; stored in `backend/data/mpas.geojson`
- **Current coverage:** 28 real marine MPAs around Sri Lanka (including Bar Reef Marine Sanctuary)
- **Backend serves:** `GET /mpa` (FeatureCollection), `GET /mpa/status`
- **Spatial scoring:** `mpa_index.py` uses Shapely STRtree for fast nearest-MPA lookup

Refresh coverage:
```bash
cd ml
python fetch_wdpa.py --bbox 78.0 5.5 82.5 10.0   # regional (recommended)
python fetch_wdpa.py --global --simplify           # all ~10,800 marine MPAs
```

### Sentinel-1 / Sentinel Hub (CDSE) — On-demand SAR Imagery
- **Provider:** Copernicus Data Space Ecosystem (free tier)
- **Auth:** OAuth2 client credentials (`SENTINELHUB_CLIENT_ID`, `SENTINELHUB_CLIENT_SECRET`)
- **How used:** YOLO service fetches a 640×640 SAR chip for a given lat/lon/date when an officer runs a point verify or sweep
- **Status:** ⚠️ Experimental — domain gap means detections fire at ~0.15 conf, below 0.45 threshold

### OpenStreetMap — Port Data
- **Source:** Overpass API (`https://overpass-api.de/api/interpreter`)
- **Query:** `node["leisure"="marina"]` near monitored bbox
- **Stored as:** `backend/data/ports.json` (static)
- **Used for:** `distance_from_port_km` context in evidence cards

---

## GFW Demo Detections (Bar Reef seed data)

The 4 dark-vessel detections near Bar Reef Marine Sanctuary used in the demo:

| id | lat | lon | dist to MPA | near_mpa | risk_score | risk_level |
|---|---|---|---|---|---|---|
| bar-reef-001 | 8.66 | 79.75 | ~14.1 km | false | ~0.46 | MEDIUM |
| bar-reef-002 | 8.48 | 79.58 | ~11.5 km | false | ~0.46 | MEDIUM |
| **bar-reef-003** | **8.51** | **79.68** | **0.4 km** | **true** | **0.61** | **HIGH** ← headline demo |
| bar-reef-004 | 8.68 | 79.69 | ~16.5 km | false | ~0.46 | MEDIUM |

All: `ais_matched=false`, `ais_data_available=true`, `detection_conf=0.70`, `image_quality_score=1.0`.
