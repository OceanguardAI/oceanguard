# OceanGuard Live Data Pipeline

Status of each live detection feed and how to operate it.

## Detection feeds

| Feed | Status | Source | Notes |
|------|--------|--------|-------|
| **GFW SAR** | ✅ **Production** | Global Fishing Watch API | Dark vessels + server-side AIS cross-match. Auto-loads at backend startup. |
| **AISStream** | ✅ Production | aisstream.io WebSocket | Live AIS to confirm dark detections (`POST /ais/verify-dark`). |
| **WDPA marine MPAs** | ✅ Production | UNEP-WCMC WDPA (open ArcGIS) | Real protected-area polygons. Nearest-MPA scoring + map layer. No token. |
| **Sentinel-1 → YOLO** | ⚠️ **Experimental** | Copernicus + `best.pt` | Domain gap: model trained on xView3 fires at ~0.15 conf on Sentinel-1, below the 0.45 threshold. See below. |

## Marine Protected Areas (WDPA) — live

The protected-area layer comes from the public UNEP-WCMC World Database on
Protected Areas (no token). `backend/data/mpas.geojson` ships with the 28 real
marine MPAs around Sri Lanka (including Bar Reef Marine Sanctuary). The backend:

- serves the whole layer at `GET /mpa` (FeatureCollection)
- reports `GET /mpa/status` — count + source file
- scores every detection against the **nearest** MPA in the set
  (`app/services/mpa_index.py`), not a single hardcoded polygon

Refresh or widen coverage with the downloader (creds-free):

```bash
cd ml
python fetch_wdpa.py --bbox 78.0 5.5 82.5 10.0   # a region (recommended)
python fetch_wdpa.py --global --simplify          # all ~10,800 marine MPAs (large)
```

The committed `mpas.geojson` is the regional seed. If it is absent the system
falls back to the single `bar_reef.geojson` so the map always renders.

## Production path (GFW) — already live

The backend ingests GFW SAR detections at startup (`GFW_INGEST_ON_STARTUP=true`)
and exposes:

- `GET  /ingest/status` — feed config + events loaded
- `POST /ingest/gfw` — manual refresh (persists snapshot)
- `GET  /ais/live?seconds=20` — live AIS snapshot over the bbox
- `POST /ais/verify-dark` — confirm which dark detections have no nearby AIS

Credentials live in `backend/.env` (local) and GitHub Secrets/Vars (Cloud Run):
`GFW_API_TOKEN`, `AISSTREAM_API_KEY`, `GFW_REGION_BBOX`, `GFW_LOOKBACK_DAYS`.

## Experimental path (Sentinel-1 → YOLO)

The pipeline is complete and runs end-to-end, but is **not production-trusted**
because of a sensor domain gap (see `ml/run_live_pipeline.py` header).

Run it (creds in `ml/.env` — see `ml/.env.example`):

```bash
cd ml
python run_live_pipeline.py --backend-url http://localhost:8000
# or offline on a local scene:
python run_live_pipeline.py --tif-path data/scene.tif
```

It fetches a 10 m, most-recent Sentinel-1 window centered on the bbox, runs
`best.pt`, georeferences against the scene's own transform, scores risk, and
POSTs events to `/ingest/push?mode=merge`.

**To make it production-trusted**, pick one: fine-tune `best.pt` on Sentinel-1
vessel chips, add Sentinel-1 preprocessing alignment, or validate a
Sentinel-1-specific confidence threshold against AIS ground truth.

## Security

API keys/secrets are gitignored (`backend/.env`, `ml/.env`). Rotate any key that
was shared in plaintext.
