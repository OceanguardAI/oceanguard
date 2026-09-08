# System Health and Recovery Plan

Last checked: 2026-09-08

## 1. Current live services

OceanGuard is deployed as three Cloud Run services:

| Service | Purpose | Current status |
|---|---|---|
| `oceanguard-web` | Vite frontend | Ready |
| `oceanguard-api` | Main FastAPI backend | Ready |
| `oceanguard-yolo` | On-demand SAR/YOLO inference | Ready |

Current public URLs:

| Service | URL |
|---|---|
| Frontend | `https://oceanguard-web-ezas7zp4yq-el.a.run.app` |
| Backend API | `https://oceanguard-api-ezas7zp4yq-el.a.run.app` |
| YOLO service | `https://oceanguard-yolo-ezas7zp4yq-el.a.run.app` |

The project also has the stable project-number Cloud Run aliases:

| Service | URL |
|---|---|
| Frontend alias | `https://oceanguard-web-26506540964.asia-south1.run.app` |
| Backend alias | `https://oceanguard-api-26506540964.asia-south1.run.app` |
| YOLO alias | `https://oceanguard-yolo-26506540964.asia-south1.run.app` |

## 2. Verified working areas

The following live checks passed:

| Check | Result |
|---|---|
| Frontend root page | `200 OK` |
| Backend `/health` | `200 OK` |
| Backend `/risk-summary` | `200 OK` |
| Backend `/risk-events` | `200 OK` |
| Backend `/model-metrics` | `200 OK` |
| Backend `/agents/status` | `200 OK` |
| Backend `/ingest/status` | `200 OK` |
| Backend `/mpa/status` | `200 OK` |
| Backend `/sar-image/status` | `200 OK` |
| Backend `/verify/yolo/status` | `200 OK` |
| YOLO `/health` | `200 OK` |
| Backend Sentinel chip fetch | `200 OK`, image returned |
| AISStream sample | `200 OK`, live vessels returned |
| YOLO live point check | `200 OK`, inference completed |
| CORS from main frontend URL | `200 OK` |
| CORS from project-number frontend alias | `200 OK` after manual Cloud Run update |

Local validation also passed:

| Check | Result |
|---|---|
| Backend tests using `backend/.venv` | `58 passed` |
| ML tests | `20 passed`, `2 skipped` |
| Frontend production build | Passed |

## 3. Current degraded or broken areas

### 3.1 Gemini / Vertex AI agent calls

Observed behavior:

- `/agents/status` reports Gemini provider mode as `gcp`
- the SDK is importable
- the Gemini client can be created
- actual agent calls fall back instead of using Gemini

Cloud Run logs show:

```text
403 PERMISSION_DENIED
Lightning dunning decision is deny for project: projects/26506540964
```

What this means:

- this is not a missing SDK issue
- this is not a missing `roles/aiplatform.user` issue
- this is not because `aiplatform.googleapis.com` is disabled
- the denial is coming from the Google billing/quota/account side for Gemini/Vertex model usage

Confirmed GCP state:

- `aiplatform.googleapis.com` is enabled
- project billing is linked and marked enabled
- `oceanguard-runtime@oceaneyelabs.iam.gserviceaccount.com` has `roles/aiplatform.user`

Most likely fix:

- open Google Cloud Billing for the linked billing account
- check for account holds, credit exhaustion, overdue payment, or Gemini/Vertex usage restrictions
- after clearing billing/account state, redeploy or restart `oceanguard-api`
- verify with `POST /agents/ask`

### 3.2 Global Fishing Watch live SAR ingest

Observed behavior:

- `/ingest/status` shows `gfw_token_configured=true`
- `/ingest/gfw` returned `200 OK`
- the returned ingest count was `0`
- Cloud Run logs show startup ingest loaded `0` GFW SAR events
- direct follow-up GFW diagnostics returned `429 Too Many Requests`

The GFW error said the application token is allowed only one concurrent report and that a whole-world report was already running.

What this means:

- the token is present
- this does not look like an expired-token error
- the current whole-world GFW query is too heavy and can lock the token
- Cloud Run autoscaling can make this worse because each new backend instance may start a live ingest

Most likely fixes:

- stop using startup whole-world GFW ingest for every Cloud Run instance
- move GFW ingest to one controlled job or manual refresh path
- use smaller region bboxes for demo-critical areas
- add a cooldown/backoff when GFW returns `429`
- optionally store the last successful live ingest result so the UI does not fall back to stale seed data

### 3.3 Backend CORS durable configuration

Observed behavior:

- CORS preflight from `https://oceanguard-web-ezas7zp4yq-el.a.run.app` passed
- CORS preflight from `https://oceanguard-web-26506540964.asia-south1.run.app` originally failed with `400`
- the live Cloud Run backend was manually updated and both origins now pass

What this means:

- the current live backend accepts both frontend URLs
- the GitHub Actions variable still needs the same value, otherwise a future backend workflow deploy can overwrite the live fix

Required durable fix:

Set `CORS_ORIGINS` to include both frontend origins:

```text
https://oceanguard-web-ezas7zp4yq-el.a.run.app,https://oceanguard-web-26506540964.asia-south1.run.app
```

This should be updated in:

- GitHub Actions variable `CORS_ORIGINS`
- Cloud Run backend environment if doing an immediate manual repair

### 3.4 Secret handling in Cloud Run

Observed behavior:

- Cloud Run currently receives several API credentials as plain environment values
- Secret Manager exists in the project
- Secret Manager currently lists `GFW_API_TOKEN` and `AISSTREAM_API_KEY`
- Sentinel Hub secrets were not visible in Secret Manager during this check

Why this matters:

- plain Cloud Run environment values are easier to expose through service description access
- Secret Manager gives better rotation, IAM, auditing, and safer deployment behavior

Required fix:

- store all external credentials in Secret Manager
- update Cloud Run deploy workflows to use secret references instead of writing secret values into env YAML

Secrets that should live in Secret Manager:

- `GFW_API_TOKEN`
- `AISSTREAM_API_KEY`
- `SENTINELHUB_CLIENT_ID`
- `SENTINELHUB_CLIENT_SECRET`

GitHub Actions can still hold deployment-only credentials and repo variables, but runtime API keys should be read by Cloud Run from Secret Manager.

## 4. Recommended recovery order

### Step 1: Fix backend fallback-agent routing

Status: done in code.

The fallback ask agent now answers exact metrics/count questions before broad methodology explanations.

Why this matters:

- if Gemini is unavailable, the dashboard assistant still answers useful project questions
- local backend tests pass again

### Step 2: Fix CORS for both frontend URLs

Live status: fixed manually on Cloud Run.

Durable GitHub Actions follow-up:

Update GitHub variable:

```text
CORS_ORIGINS=https://oceanguard-web-ezas7zp4yq-el.a.run.app,https://oceanguard-web-26506540964.asia-south1.run.app
```

Then redeploy backend through GitHub Actions:

```text
GitHub -> Actions -> Deploy OceanGuard Backend to Cloud Run -> Run workflow -> main
```

Immediate CLI repair option:

```powershell
gcloud run services update oceanguard-api `
  --region asia-south1 `
  --update-env-vars "^|^CORS_ORIGINS=https://oceanguard-web-ezas7zp4yq-el.a.run.app,https://oceanguard-web-26506540964.asia-south1.run.app"
```

This CLI repair was already applied during the 2026-09-08 health pass.

### Step 3: Move runtime API credentials to Secret Manager

Create missing Sentinel Hub secrets:

```powershell
gcloud secrets create SENTINELHUB_CLIENT_ID --replication-policy=automatic
gcloud secrets create SENTINELHUB_CLIENT_SECRET --replication-policy=automatic
```

Add or rotate secret versions:

```powershell
gcloud secrets versions add GFW_API_TOKEN --data-file=-
gcloud secrets versions add AISSTREAM_API_KEY --data-file=-
gcloud secrets versions add SENTINELHUB_CLIENT_ID --data-file=-
gcloud secrets versions add SENTINELHUB_CLIENT_SECRET --data-file=-
```

Grant the runtime service account access:

```powershell
gcloud secrets add-iam-policy-binding GFW_API_TOKEN `
  --member="serviceAccount:oceanguard-runtime@oceaneyelabs.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding AISSTREAM_API_KEY `
  --member="serviceAccount:oceanguard-runtime@oceaneyelabs.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding SENTINELHUB_CLIENT_ID `
  --member="serviceAccount:oceanguard-runtime@oceaneyelabs.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding SENTINELHUB_CLIENT_SECRET `
  --member="serviceAccount:oceanguard-runtime@oceaneyelabs.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
```

Then update backend and YOLO deployment workflows to use Cloud Run secret references.

### Step 4: Repair Gemini / Vertex AI access

Check these in Google Cloud Console:

- Billing account has no hold
- free credits are still active or billing is upgraded
- Vertex AI Gemini usage is allowed for project `oceaneyelabs`
- project quota is available for `gemini-2.5-flash`

Then smoke test:

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri "https://oceanguard-api-ezas7zp4yq-el.a.run.app/agents/ask" `
  -ContentType "application/json" `
  -Body '{"question":"What is the highest risk detection?"}'
```

A healthy result should come from Gemini without a `403` appearing in Cloud Run logs.

### Step 5: Change GFW ingestion strategy

Recommended production behavior:

- disable automatic whole-world ingest on every backend startup
- add a scheduled single Cloud Run Job or Cloud Scheduler call for refresh
- use a narrower bbox for demo refreshes
- use cached last-known-good results when GFW is busy
- add `429` handling with a clear message like "GFW report already running; retry later"

Suggested short-term hackathon setting:

```text
GFW_REGION_BBOX=78.0,5.5,82.5,10.0
GFW_LOOKBACK_DAYS=30
GFW_MAX_EVENTS=600
GFW_INGEST_ON_STARTUP=false
```

Then trigger refresh manually only when needed:

```powershell
Invoke-RestMethod -Method POST -Uri "https://oceanguard-api-ezas7zp4yq-el.a.run.app/ingest/gfw"
```

Suggested longer-term setting:

- keep global MPA data
- fetch GFW by region tiles instead of one huge world polygon
- run one scheduled ingest worker
- persist latest live events outside process memory

### Step 6: Redeploy in this order

1. Backend after CORS, Gemini, secret, and GFW config changes
2. YOLO after Sentinel Hub secrets are moved to Secret Manager
3. Frontend only if `VITE_API_BASE_URL` changes

## 5. Final smoke test checklist

Run these after the recovery changes:

```powershell
$api = "https://oceanguard-api-ezas7zp4yq-el.a.run.app"
$web = "https://oceanguard-web-ezas7zp4yq-el.a.run.app"
$yolo = "https://oceanguard-yolo-ezas7zp4yq-el.a.run.app"

Invoke-RestMethod "$api/health"
Invoke-RestMethod "$api/risk-summary"
Invoke-RestMethod "$api/model-metrics"
Invoke-RestMethod "$api/agents/status"
Invoke-RestMethod "$api/ingest/status"
Invoke-RestMethod "$api/mpa/status"
Invoke-RestMethod "$api/sar-image/status"
Invoke-RestMethod "$api/verify/yolo/status"
Invoke-RestMethod "$yolo/health"
Invoke-WebRequest "$web" -UseBasicParsing
```

Then test the live integrations:

```powershell
Invoke-RestMethod -Method POST -Uri "$api/agents/ask" -ContentType "application/json" -Body '{"question":"Which detection is highest risk?"}'
Invoke-WebRequest "$api/sar-image?lat=8.66&lon=79.75" -UseBasicParsing
Invoke-RestMethod "$api/ais/live?seconds=5"
Invoke-RestMethod -Method POST -Uri "$api/ingest/gfw"
```

## 6. Current plain-English status

The application is online and usable, but it is not fully healthy.

Working:

- frontend loads
- backend routes serve
- seed detections load
- model metrics serve
- global MPA index loads
- Sentinel Hub chip fetch works
- YOLO service works
- AISStream works

Needs repair:

- Gemini/Vertex AI is blocked by a GCP billing/quota/account denial
- GFW whole-world ingest is currently rate-limited/locked and returning no live events
- CORS is fixed live, but the GitHub `CORS_ORIGINS` variable should be updated to preserve it
- runtime credentials should be moved from plain Cloud Run env vars to Secret Manager references
