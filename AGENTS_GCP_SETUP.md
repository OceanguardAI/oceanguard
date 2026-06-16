# OceanGuard AI — Agents Setup From GCP

This guide is the shortest path to run the OceanGuard backend agents from Google Cloud Gemini instead of a plain API key.

It is focused only on the agent setup path:

- `narrator`
- `briefing`
- `patrol`
- `ask`

If you want the broader Gemini docs too, see [GCP_GEMINI_SETUP.md](/d:/PROJECTS/AI_ML/OceanEye/GCP_GEMINI_SETUP.md).

---

## 1. What we are using

Our backend supports a Google Cloud Gemini mode with these settings:

```text
GEMINI_USE_GCP=true
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-3.5-flash
```

When this mode is active:

- `/agents/status` should show `provider_mode: "gcp"`
- the backend authenticates with Google Cloud credentials
- `GEMINI_API_KEY` is not required

---

## 2. Google Cloud setup

### Create or choose a project

Use a Google Cloud project where billing is enabled.

### Enable the Gemini service

In Google Cloud Console:

1. Open your project.
2. Go to `APIs & Services`.
3. Enable the Gemini / Vertex-style Gemini service used by the Gen AI SDK.

### Install and configure gcloud

```powershell
gcloud init
gcloud config set project YOUR_PROJECT_ID
```

---

## 3. Create local credentials

For local development, use Application Default Credentials:

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

This is the easiest way to let the backend call Gemini from your machine.

---

## 4. Configure the backend

### Local backend run

```powershell
cd backend
copy .env.example .env
```

Put this in `backend/.env`:

```text
GEMINI_USE_GCP=true
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-3.5-flash
```

Keep `GEMINI_API_KEY=` empty for this path.

### Docker run

If you use `docker-compose`, also put these in the repo-root `.env`:

```text
GEMINI_USE_GCP=true
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-3.5-flash
```

---

## 5. Start the backend

### PowerShell local run

```powershell
cd backend
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 6. Verify the agents are on GCP mode

Run:

```powershell
curl http://localhost:8000/agents/status
```

Expected important fields:

```json
{
  "provider": "gemini",
  "provider_mode": "gcp",
  "provider_enabled": true,
  "provider_importable": true,
  "client_ready": true,
  "fallback_mode": false
}
```

Meaning:

- `provider_mode: "gcp"` means it is using the Google Cloud path
- `client_ready: true` means the Gemini client was created successfully
- `fallback_mode: false` means requests should go to Gemini, not fallback templates

---

## 7. Test our agents

### Narrator

```powershell
curl -X POST http://localhost:8000/agents/narrate/bar-reef-003
```

### Briefing

```powershell
curl -X POST http://localhost:8000/agents/briefing/current
```

### Patrol

```powershell
curl -X POST http://localhost:8000/agents/patrol/current
```

### Ask

```powershell
curl -X POST http://localhost:8000/agents/ask -H "Content-Type: application/json" -d "{\"question\":\"Which detection is highest risk?\"}"
```

If these return generated Gemini text instead of the usual deterministic fallback wording, the setup is working.

---

## 8. Cloud Run deployment idea

For Cloud Run, prefer a service account attached to the service instead of storing a JSON key file.

Set these environment variables in the Cloud Run service:

```text
GEMINI_USE_GCP=true
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-3.5-flash
```

Usually you do not need `GOOGLE_APPLICATION_CREDENTIALS` there, because ADC resolves from the attached service account.

---

## 9. If it does not work

- `provider_mode` is `api_key`
  `GEMINI_USE_GCP=true` is not reaching the backend process.
- `provider_enabled` is `false`
  `GOOGLE_CLOUD_PROJECT` is missing or empty.
- `client_ready` is `false`
  credentials, API enablement, or SDK setup is incomplete.
- agent routes still fall back
  the client was created, but the live Gemini request failed. Check project access, quota, and ADC again.

---

## 10. Recommended path

For local development, use:

1. `gcloud auth application-default login`
2. `backend/.env` with `GEMINI_USE_GCP=true`
3. local `uvicorn` run
4. `curl http://localhost:8000/agents/status`

That is the cleanest way to run our agents from GCP.
