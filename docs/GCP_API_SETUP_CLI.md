# OceanGuard AI — GCP API Setup From CLI

This file is the CLI checklist for running OceanGuard's backend agents from Google Cloud Gemini and deploying the backend to Cloud Run through GitHub Actions.

---

## Project values

```text
PROJECT_ID=oceaneyelabs
PROJECT_NUMBER=26506540964
REGION=asia-south1
ARTIFACT_REGISTRY_LOCATION=asia-south1
ARTIFACT_REGISTRY_REPOSITORY=oceanguard
CLOUD_RUN_SERVICE=oceanguard-api
RUNTIME_SERVICE_ACCOUNT=oceanguard-runtime@oceaneyelabs.iam.gserviceaccount.com
DEPLOYER_SERVICE_ACCOUNT=github-deployer@oceaneyelabs.iam.gserviceaccount.com
```

---

## 1. Local ADC login

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project oceaneyelabs
```

---

## 2. One-time GCP setup script

Run:

```powershell
.\scripts\setup_gcp_oceanguard.ps1
```

The script will prompt for:

- `GITHUB_OWNER`
- `GITHUB_REPO`

It will:

- set the active project
- enable required APIs
- create Artifact Registry if missing
- create service accounts if missing
- grant IAM roles
- create the Workload Identity Pool and provider if missing
- print `WIF_PROVIDER` and `WIF_SERVICE_ACCOUNT` for GitHub Actions variables

---

## 3. Optional secret creation

Example:

```powershell
.\scripts\create_secret.ps1 -Name GFW_TOKEN -Value "paste-token-here"
```

This creates the secret if missing, adds a new version, and grants the runtime service account `secretAccessor`.

---

## 4. Backend local run

```powershell
cd backend
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 5. Local test commands

```powershell
curl http://localhost:8000/agents/status
curl -X POST http://localhost:8000/agents/narrate/bar-reef-003
curl -X POST http://localhost:8000/agents/briefing/current
curl -X POST http://localhost:8000/agents/patrol/current
curl -X POST http://localhost:8000/agents/ask -H "Content-Type: application/json" -d "{\"question\":\"Which detection is highest risk?\"}"
```

Expected important status fields:

```text
provider_mode: gcp
provider_enabled: true
client_ready: true
fallback_mode: false
```

---

## 6. GitHub Actions variables

After running `.\scripts\setup_gcp_oceanguard.ps1`, add these in:

`GitHub repo -> Settings -> Secrets and variables -> Actions -> Variables`

Variables:

- `WIF_PROVIDER`
- `WIF_SERVICE_ACCOUNT`

---

## 7. Deployment behavior

Workflow file:

`/.github/workflows/deploy-backend.yml`

It will:

- trigger on pushes to `main`
- rebuild only when `backend/**` or the workflow changes
- authenticate with Workload Identity Federation
- build and push the backend image to Artifact Registry
- deploy `oceanguard-api` to Cloud Run in `asia-south1`
- set:
  - `GEMINI_USE_GCP=true`
  - `GOOGLE_CLOUD_PROJECT=oceaneyelabs`
  - `GOOGLE_CLOUD_LOCATION=global`
  - `GEMINI_MODEL=gemini-3.5-flash`
