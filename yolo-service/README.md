# OceanGuard YOLO SAR Service

On-demand vessel verification with our own fine-tuned model. Kept as a **separate
Cloud Run service** so the heavy `torch` / `ultralytics` stack (and its cold
start) never burdens the main API. Scales to zero between requests — it costs
nothing until an officer runs a check.

## Why it exists

A truly *dark* vessel switches its AIS transponder **off**, so the AIS-based feed
(GFW) cannot identify it. The hull still reflects radar, so our model (`best.pt`,
YOLO11n fine-tuned on HRSID Sentinel-1 SAR) can confirm a contact the AIS path
misses. This is the manual-review safety net: the officer points at a suspect
detection and asks our own model to look at the live radar.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/health` | Liveness + whether the model and Sentinel Hub are ready |
| `POST` | `/detect-point` | `{lat, lon, date?}` → fetch a tight high-res Sentinel-1 chip, run YOLO, return detections (boxes + confidence + lat/lon) and the analysed chip as base64 PNG |

The main API proxies to this service at `POST /verify/yolo?event_id=` and, when a
vessel is confirmed, raises the event's risk ("confirmed by 2 independent
systems").

## How a point becomes a detection

```
{lat, lon, date}
  → Sentinel Hub: fetch a ~4.4 km VV chip at 640 px (~7 m/px, close to the
    model's training resolution) for the 12 days up to `date`
  → best.pt inference (CPU)
  → map detection pixels → lat/lon via the chip's bbox
  → return boxes + confidence + the exact chip the model saw
```

## Configuration (env)

| Var | Meaning |
|---|---|
| `SENTINELHUB_CLIENT_ID` / `SENTINELHUB_CLIENT_SECRET` | Sentinel Hub OAuth (same pair the backend uses for chips) |
| `CONF_THRESHOLD` | Detection confidence floor (default `0.25`) |
| `CORS_ORIGINS` | Allowed origins (default `*`) |

## Deploy

Pushed to `main` under `yolo-service/**`, GitHub Actions
(`.github/workflows/deploy-yolo.yml`) builds the image and deploys the
`oceanguard-yolo` Cloud Run service (2Gi / 2CPU, `min-instances=0`). After the
first deploy, copy the service URL into the repo variable `YOLO_SERVICE_URL` and
redeploy the backend so it can reach this service.

## Local run

```bash
cd yolo-service
pip install -r requirements.txt
export SENTINELHUB_CLIENT_ID=... SENTINELHUB_CLIENT_SECRET=...
uvicorn app.main:app --reload --port 8081
```
