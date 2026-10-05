# Deployment and Runtime

OceanGuard runs as three Azure Container Apps in one Container Apps environment
(`centralindia`, the region the student subscription policy allows). Images are built
inside Azure Container Registry with `az acr build`, so no local Docker engine is needed.

| App | Image | Notes |
|---|---|---|
| `og-backend` | `backend/Dockerfile` | FastAPI API and agents; 1 CPU, 2Gi; always on |
| `og-yolo` | `yolo-service/Dockerfile` | torch + ultralytics + fine-tuned weights; 2 CPU, 4Gi; scales to zero |
| `og-web` | `frontend/Dockerfile` | Static build behind nginx; `VITE_API_BASE_URL` is a build argument |

## First deploy

```powershell
pwsh scripts/azure_deploy.ps1
```

The script registers providers, creates the registry and environment, builds and
creates the three apps, wires `YOLO_SERVICE_URL` into the backend, and sets
`CORS_ORIGINS` to the web URL. Secrets (`GFW_API_TOKEN`, `AISSTREAM_API_KEY`,
`GROQ_API_KEY`, Sentinel Hub client id/secret, `ADMIN_API_KEY`) come from
`backend/.env` and are stored as Container Apps secrets referenced by name.
`ADMIN_API_KEY` is generated into `backend/.env` when empty; write routes need the
`X-API-Key` header.

## Continuous deployment

`.github/workflows/deploy-backend.yml`, `deploy-frontend.yml` and `deploy-yolo.yml`
run on pushes to `main` that touch their folder (or manually). Each signs in to Azure,
builds the image in ACR tagged with the commit SHA, and runs `az containerapp update`
to roll out a new revision. Secrets and environment variables stay as the first deploy
set them.

Repository configuration:

- secret `AZURE_CREDENTIALS`: service principal JSON scoped to the resource group
- variables `ACR_NAME`, `AZURE_RESOURCE_GROUP`, and (frontend) `VITE_API_BASE_URL`

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
