# Deployment and Runtime

OceanGuard runs as three Azure Container Apps in one Container Apps environment
(`centralindia`, the region the student subscription policy allows). Images are built by
GitHub Actions and pushed to Azure Container Registry. Azure for Students blocks ACR
Tasks (`az acr build` fails with `TasksOperationsNotAllowed`), so cloud builds are not an
option and no local Docker engine is needed.

| App | Image | Notes |
|---|---|---|
| `og-backend` | `backend/Dockerfile` | FastAPI API and agents; 1 CPU, 2Gi; always on |
| `og-yolo` | `yolo-service/Dockerfile` | torch + ultralytics + fine-tuned weights; 2 CPU, 4Gi; scales to zero |
| `og-web` | `frontend/Dockerfile` | Static build behind nginx; `VITE_API_BASE_URL` is a build argument |

## First deploy

```powershell
pwsh scripts/azure_deploy.ps1
```

The script registers providers and creates the registry, the environment and the three
apps (infrastructure only, each on a public placeholder image). It stores the secrets
(`GFW_API_TOKEN`, `AISSTREAM_API_KEY`, `GROQ_API_KEY`, Sentinel Hub client id/secret,
`ADMIN_API_KEY`) from `backend/.env` as Container Apps secrets referenced by name,
wires `YOLO_SERVICE_URL` into the backend and sets `CORS_ORIGINS` to the web URL.
`ADMIN_API_KEY` is generated into `backend/.env` when empty; write routes need the
`X-API-Key` header. Re-running leaves existing apps unchanged.

Then give GitHub Actions access and ship the real images:

```powershell
$sub = az account show --query id -o tsv
az ad sp create-for-rbac --name og-github --role Contributor `
  --scopes /subscriptions/$sub/resourceGroups/oceanguard-rg --sdk-auth   # paste into the AZURE_CREDENTIALS secret
```

Repository secret `AZURE_CREDENTIALS`; variables `ACR_NAME` (`ogacr901ad`),
`AZURE_RESOURCE_GROUP` (`oceanguard-rg`) and `VITE_API_BASE_URL` (the backend URL the
script prints). Then run the three **Deploy OceanGuard ...** workflows once from the
Actions tab.

## Continuous deployment

`.github/workflows/deploy-backend.yml`, `deploy-frontend.yml` and `deploy-yolo.yml`
run on pushes to `main` that touch their folder (or manually). Each signs in to Azure,
builds the image on the runner, pushes it to ACR tagged with the commit SHA (using the
registry admin credential fetched at run time, so no extra secret), points ingress at
port 8080 and runs `az containerapp update` to roll out a new revision. Secrets and
environment variables stay as the first deploy set them.

## Runtime behaviour

- The backend listens on `$PORT` (8080). Live GFW ingest runs in a background thread
  after startup, so the health check passes before data loads.
- State is process-local until `DATABASE_URL` points at PostgreSQL with PostGIS
  (Azure Database for PostgreSQL flexible server). Run
  `python -m app.store.migrate` before enabling it; see `backend/README.md`.
- The YOLO service cold-starts in tens of seconds after idle; the UI shows the check as
  running until it answers. It is hidden while `YOLO_SERVICE_URL` is empty.
- Model weights live in `yolo-service/models/best.pt` and are baked into the image.
  Training and evaluation run in Azure ML (see `ml/cloud/` and `scripts/azure_train_job.ps1`).
