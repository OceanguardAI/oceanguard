# Spatial Intelligence and Protected Areas Module

## 1. What this module does

This module gives OceanGuard its conservation context.

Without it, the app would only know:

- there is a vessel
- there may or may not be AIS identity data

With it, the app can answer:

- is the vessel inside a protected area?
- how far is it from a protected area?
- which protected area is nearest?
- which polygons should be shown in the current viewport?

The key files are:

- `backend/app/services/mpa_index.py`
- `backend/app/api/routes/geo.py`
- `frontend/src/components/MapView.tsx`
- `ml/fetch_wdpa.py`

## 2. Why this module matters so much

OceanGuard is not a generic vessel tracker.

Its value comes from combining vessel presence with ecological context.

That context is the difference between:

- "a ship exists somewhere"

and:

- "a dark vessel is inside or near a protected marine zone"

That is why MPA intelligence is not just a map decoration. It is part of the risk engine.

## 3. How protected areas are stored

The backend expects protected-area geometry in `backend/data/`.

Current behavior in `geo.py`:

- if `mpas.geojson` exists, use it
- otherwise fall back to `bar_reef.geojson`

This means the system supports two modes:

### Full multi-MPA mode

- global or large-scale MPA data
- backed by `mpas.geojson`

### Fallback single-area mode

- smaller offline/demo-safe fallback
- backed by `bar_reef.geojson`

This is a practical resilience feature.

## 4. The MPA index design

The heavy lifting lives in `backend/app/services/mpa_index.py`.

It builds an `MPAIndex` with:

- geometry list
- area names
- a Shapely `STRtree`

That STRtree is crucial.

Why:

- naïvely scanning all polygons for every detection would be too slow
- a spatial index gives much better lookup behavior
- this matters when scoring large global ingest sets

This is one of the strongest technical choices in the repo.

## 5. What the index can do

The index currently supports two main spatial operations.

### A. `nearest(lat, lon)`

Returns:

- `mpa_name`
- `distance_km`
- `inside_mpa`
- `near_mpa`

This is used by live risk scoring.

### B. `features_in_bbox(...)`

Returns a GeoJSON `FeatureCollection` containing only the MPAs intersecting a given bbox.

This is used by the frontend map.

These are two different but complementary responsibilities:

- backend scoring
- frontend rendering

## 6. How "inside" vs "near" is computed

### Inside

If the point intersects a polygon:

- `inside_mpa = true`
- `distance_km = 0.0`

This is checked using the spatial index first.

### Near

If not inside:

- the system finds the nearest polygon
- computes the nearest point on that polygon
- converts that into great-circle distance

Current near threshold:

- `NEAR_MPA_KM = 10.0`

This is separate from the broader scoring bands in `gfw_ingest.py`.

That distinction matters:

- the MPA module defines geometric meaning
- the risk module decides how much that meaning affects score

## 7. Why the backend serves viewport-filtered MPAs

The frontend map does not request the entire global MPA dataset every time.

Instead, `MapView.tsx` sends the current viewport bbox.

Then:

- `geo.py` calls `mpa_index.get_index().features_in_bbox(...)`
- only intersecting polygons are returned

Why this is important:

- full global polygon delivery would be heavy
- browser rendering would become expensive
- mobile responsiveness would suffer

This is an example of doing spatial filtering on the server, where it belongs.

## 8. How the frontend uses this module

The spatial UI flow is mostly in `frontend/src/components/MapView.tsx`.

### `MpaLayer`

Responsibilities:

- watch map movement
- debounce requests
- compute viewport bbox
- request MPAs for that bbox
- transform GeoJSON into Leaflet polygon shapes

### `featuresToShapes`

Why it exists:

- GeoJSON can contain `Polygon` or `MultiPolygon`
- Leaflet wants coordinates in a different form

So the helper normalizes server geometry into renderable frontend shape objects.

## 9. Relationship to risk scoring

This module does not decide overall risk by itself.

Instead it supplies:

- whether a detection is inside an MPA
- whether it is near an MPA
- the exact distance
- the name of the nearest protected area

Then other modules use that information:

### Live ingest scoring

`backend/app/services/gfw_ingest.py`

### Offline ML scoring

`ml/pipeline/risk.py`

### UI rendering

- marker popups
- Evidence Card fields
- queue labels
- assistant responses

## 10. Relationship to ports

`geo.py` also serves port reference data through `/ports`.

Ports are a secondary context layer.

They help answer questions like:

- how far is this contact from a known port?

That can be useful for operator interpretation even though it is not the main ecological signal.

## 11. How this module supports the SAR/YOLO features

Spatial context is also part of the SAR verification story.

Examples:

- a YOLO-confirmed contact inside an MPA is more interesting than one in open water
- a point scan can be run on an arbitrary place, but MPA geometry helps interpret that place
- an area sweep becomes more meaningful when the viewport is centered around a protected area

That means the MPA module and the SAR module are tightly related even though they are separate code paths.

## 12. How the data likely entered the repo

The repo also contains `ml/fetch_wdpa.py`.

That script is the preparation seam for MPA source data.

Conceptually, the pipeline is:

1. fetch protected-area data
2. simplify/prepare it into project-friendly GeoJSON
3. place it in backend data directory
4. load and index it at runtime

This is an important example of how offline preparation and live runtime meet in the project.

## 13. If you want to modify this module

### Change spatial thresholds

Start with:

- `backend/app/services/mpa_index.py`
- `backend/app/services/gfw_ingest.py`
- `ml/pipeline/risk.py`

### Change MPA serving behavior

Start with:

- `backend/app/api/routes/geo.py`
- `frontend/src/components/MapView.tsx`

### Change source datasets

Start with:

- `ml/fetch_wdpa.py`
- current files in `backend/data/`

### Add named-MPA actions

Good entry points:

- `frontend/src/components/MapView.tsx`
- `backend/app/api/routes/geo.py`
- `backend/app/services/mpa_index.py`

## 14. Bottom line

This module is the conservation brain of OceanGuard.

It transforms plain vessel detection into protected-area-aware monitoring, which is the reason the system can rank ecological relevance instead of just plotting ships.
