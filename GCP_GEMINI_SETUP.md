# OceanGuard AI — Gemini Setup From Google Cloud

**Status: Ready to use.** This guide covers the Google Cloud Gemini path for OceanGuard AI using the `google-genai` SDK with `vertexai=True`. It is separate from [API_SETUP.md](/d:/PROJECTS/AI_ML/OceanEye/API_SETUP.md), which covers the simpler Gemini Developer API key path.

As of **June 16, 2026**, Google’s managed GCP Gemini docs refer to this platform as **Gemini Enterprise Agent Platform**, while the Python SDK examples still use `vertexai=True`. In this repo, the backend now supports both auth modes:

- `provider_mode: "api_key"` for `GEMINI_API_KEY`
- `provider_mode: "gcp"` for Google Cloud project + ADC/service-account auth

---

## What this repo expects

To use the GCP path, set these backend environment variables:

```text
GEMINI_USE_GCP=true
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

You do **not** need `GEMINI_API_KEY` when `GEMINI_USE_GCP=true`.

Authentication comes from Google Cloud credentials, not from an API key:

- local development: Application Default Credentials (ADC)
- Docker: a mounted service-account JSON or another working ADC path
- Cloud Run / GCE / GKE: the attached workload/service account

---

## Official references

- Gemini Enterprise Agent Platform quickstart:
  https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start
- Google Gen AI SDK overview:
  https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/sdks/overview
- ADC local setup:
  https://docs.cloud.google.com/docs/authentication/set-up-adc-local-dev-environment
- Developer API vs Google Cloud migration notes:
  https://ai.google.dev/gemini-api/docs/migrate-to-cloud

---

## 1. Set up the Google Cloud project

1. Create or select a Google Cloud project.
2. Make sure billing is enabled for that project.
3. Enable the Gemini Enterprise Agent Platform API in the Google Cloud console.
4. Install the Google Cloud CLI if it is not already installed.
5. Initialize gcloud:

```powershell
gcloud init
gcloud config set project YOUR_PROJECT_ID
```

If you are using a federated identity, sign in to `gcloud` with that identity first, then continue.

---

## 2. Create local ADC credentials

Google’s recommended local auth path is ADC.

Run:

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

The second command helps avoid quota-project errors when local user credentials are used.

---

## 3. Configure OceanGuard for GCP Gemini

### Local backend run

```powershell
cd backend
copy .env.example .env
```

Edit `backend/.env` so it includes:

```text
GEMINI_USE_GCP=true
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-3.5-flash
```

You can leave `GEMINI_API_KEY=` blank.

### Repo-root Docker env

If you want Docker to receive the same settings, also set them in the repo-root `.env`:

```text
GEMINI_USE_GCP=true
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-3.5-flash
```

---

## 4. Run locally with PowerShell

This is the easiest GCP path because it uses your local ADC credentials directly.

```powershell
cd backend
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify:

```powershell
curl http://localhost:8000/agents/status
```

Expected shape:

```json
{
  "provider": "gemini",
  "provider_mode": "gcp",
  "provider_enabled": true,
  "provider_importable": true,
  "client_ready": true,
  "fallback_mode": false,
  "model": "gemini-3.5-flash"
}
```

Then test a live route:

```powershell
curl -X POST http://localhost:8000/agents/narrate/bar-reef-003
curl -X POST http://localhost:8000/agents/ask -H "Content-Type: application/json" -d "{\"question\":\"Which detection is highest risk?\"}"
```

---

## 5. Docker option

The repo’s `docker-compose.yml` now forwards these GCP-related variables into the backend container:

- `GEMINI_USE_GCP`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `GOOGLE_APPLICATION_CREDENTIALS`

For local Docker, the simplest secure path is to use a service-account JSON file and mount it read-only into the container.

Example override:

```yaml
services:
  backend:
    environment:
      GEMINI_USE_GCP: "true"
      GOOGLE_CLOUD_PROJECT: "your-project-id"
      GOOGLE_CLOUD_LOCATION: "global"
      GOOGLE_APPLICATION_CREDENTIALS: "/app/secrets/gcp-sa.json"
    volumes:
      - ./backend/data:/app/data
      - ./secrets/gcp-sa.json:/app/secrets/gcp-sa.json:ro
```

Notes:

- do not commit the JSON key file
- prefer workload identity or attached service accounts in real deployments
- local `uvicorn` is still the easiest development path if Docker auth becomes messy

---

## 6. Cloud Run or other Google Cloud runtime

For Cloud Run, GCE, or GKE, prefer attaching a service account with the needed access instead of using a JSON key file.

Set environment variables:

```text
GEMINI_USE_GCP=true
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-3.5-flash
```

In that setup, `GOOGLE_APPLICATION_CREDENTIALS` is usually not needed because ADC resolves from the runtime’s attached identity.

---

## 7. Troubleshooting

- `/agents/status` shows `provider_mode: "api_key"`:
  `GEMINI_USE_GCP` is not set to `true` in the environment the backend actually started with.
- `/agents/status` shows `provider_enabled: false`:
  `GOOGLE_CLOUD_PROJECT` is missing, empty, or not reaching the backend process.
- `/agents/status` shows `client_ready: false`:
  the SDK is not importable or the GCP settings are incomplete.
- agent routes fall back even though status looks ready:
  client creation succeeded, but the live request failed upstream. Recheck API enablement, project permissions, quota, and ADC credentials.
- you get local quota-project or auth errors:
  rerun `gcloud auth application-default login` and `gcloud auth application-default set-quota-project YOUR_PROJECT_ID`.

---

## 8. Summary

Use [API_SETUP.md](/d:/PROJECTS/AI_ML/OceanEye/API_SETUP.md) if you want the fastest API-key setup.

Use this guide if you want the Google Cloud managed path with project-level auth, ADC, and an easier path to Cloud Run or other GCP-hosted deployments.
