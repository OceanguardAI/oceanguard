# Deployment and Runtime Module

## 1. What this module covers

This module explains how OceanGuard is packaged and run in production.

The project is deployed as multiple Cloud Run services, not one giant container.

That is one of the most important operational decisions in the repo.

Main deployment files:

- `.github/workflows/deploy-backend.yml`
- `.github/workflows/deploy-frontend.yml`
- `.github/workflows/deploy-yolo.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `yolo-service/Dockerfile`
- `backend/app/core/config.py`
- `yolo-service/app/config.py`

## 2. The service split

The deployed system is currently split into at least three runtime services:

### A. Backend API service

Purpose:

- serve detections
- serve MPAs
- serve agents
- serve SAR display chips
- proxy/coordinate YOLO verification

### B. Frontend web service

Purpose:

- serve the built Vite app
- expose the operator UI publicly

### C. YOLO inference service

Purpose:

- hold the heavy Torch/Ultralytics runtime
- fetch tight SAR chips
- run model inference on demand

Why this split is good:

- keeps the API leaner
- avoids shipping Torch inside the main backend
- allows each service to scale on its own
- reduces operational coupling

## 3. GitHub Actions deployment model

The repo uses GitHub Actions as the CI/CD entrypoint.

Current workflow split:

- backend workflow watches backend changes
- frontend workflow watches frontend changes
- YOLO workflow watches yolo-service changes

This is a good production pattern because it avoids rebuilding every service for unrelated changes.

## 4. Backend deploy workflow

The backend workflow currently:

1. checks out the repo
2. authenticates to Google Cloud using Workload Identity Federation
3. logs Docker into Artifact Registry
4. builds the backend image
5. pushes the image
6. writes a Cloud Run env YAML file
7. deploys the service to Cloud Run

Important runtime config passed in this workflow includes:

- Gemini settings
- CORS settings
- GFW token
- AISStream key
- GFW region/lookback/event cap
- Sentinel Hub credentials
- `YOLO_SERVICE_URL`

Important operational tuning:

- runtime service account passed through `--service-account`
- memory and CPU explicitly set
- `--no-cpu-throttling` enabled

That last one is especially important because background ingest/index work needs real CPU even after startup.

## 5. Frontend deploy workflow

The frontend workflow currently:

1. checks out the repo
2. authenticates to Google Cloud
3. logs Docker into Artifact Registry
4. builds the frontend container
5. passes `VITE_API_BASE_URL` at build time
6. pushes the image
7. deploys it to Cloud Run

This build-time API variable matters because Vite injects public environment variables during build, not at runtime.

That means:

- if backend URL changes
- frontend must be rebuilt with the new variable

This is a very important detail for future maintenance.

## 6. YOLO deploy workflow

The YOLO service workflow currently:

1. checks out the repo
2. authenticates to Google Cloud
3. logs Docker into Artifact Registry
4. builds the YOLO image
5. pushes the image
6. writes a runtime env YAML file
7. deploys the YOLO service

Important runtime config includes:

- Sentinel Hub credentials
- confidence threshold
- CORS origins

Important resource tuning:

- more memory and CPU than the backend
- scale-to-zero allowed
- concurrency capped
- timeout extended

That makes sense because inference is heavier and colder than ordinary API requests.

## 7. Why Cloud Run fits this project

Cloud Run is a strong fit for this architecture because the services are:

- HTTP-based
- stateless
- containerized
- separable by responsibility

It also fits the workload shape:

- idle periods
- bursty demo traffic
- occasional heavy on-demand inference

Scale-to-zero is especially useful for:

- frontend demo deployments
- backend staging
- YOLO service cost control between officer checks

## 8. Runtime configuration philosophy

The project follows a configuration-via-environment approach.

That is good because:

- secrets do not belong in code
- different environments need different values
- Cloud Run and GitHub Actions work well with this pattern

### Backend runtime config examples

- Gemini provider mode
- GFW token
- AISStream key
- Sentinel Hub credentials
- YOLO service URL
- CORS origins

### YOLO service runtime config examples

- Sentinel Hub credentials
- model path
- confidence threshold
- chip geometry

### Frontend build config example

- `VITE_API_BASE_URL`

## 9. Artifact Registry role

Artifact Registry is the image storage layer.

The workflows:

- build local/runner containers
- tag them with commit SHA
- push them to Artifact Registry
- deploy from those pushed images

This is the correct flow because Cloud Run should deploy immutable built images, not source folders.

## 10. Workload Identity Federation

The workflows use Google GitHub Actions auth with:

- workload identity provider
- deployer service account

Why this is important:

- avoids long-lived JSON service-account keys
- is safer than storing raw credential files in GitHub secrets
- is better aligned with modern GCP CI/CD practice

## 11. Backend startup/runtime behavior in production

The backend is designed with Cloud Run startup behavior in mind.

Important runtime behavior:

- load seed events immediately
- do heavy live ingest in the background
- allow health check to pass first

This design prevents a very common cloud problem:

- slow startup
- health-check failure
- crash/restart loops

## 12. Frontend runtime behavior in production

The frontend is built into static assets and served by nginx.

Important production requirement:

- the container must listen on Cloud Run's expected port

The repo already includes:

- `frontend/nginx.conf`

This matters because static frontend deployments often fail on Cloud Run when the container still listens on port `80` instead of the expected runtime port behavior.

## 13. YOLO runtime behavior in production

The YOLO service does more than just load a model.

A typical request involves:

1. receive point request
2. fetch Sentinel-1 chip
3. decode image
4. run Ultralytics model
5. convert pixel detections back into lat/lon
6. return chip plus detections

That is why its resource profile is different from the backend.

## 14. Operational boundaries between services

This is how the services depend on each other:

### Frontend depends on backend

Through:

- `VITE_API_BASE_URL`

### Backend depends on YOLO service

Through:

- `YOLO_SERVICE_URL`

### Backend and YOLO both depend on Sentinel Hub

For:

- display chips
- inference chips

### Backend depends on GFW and AISStream

For:

- live ingest
- dark-vessel corroboration

This means the system is modular, but it is not independent piece by piece. It is a service graph.

## 15. If you want to modify this module

### Change backend deploy behavior

Start with:

- `.github/workflows/deploy-backend.yml`

### Change frontend deploy behavior

Start with:

- `.github/workflows/deploy-frontend.yml`
- `frontend/Dockerfile`
- `frontend/nginx.conf`

### Change YOLO deploy behavior

Start with:

- `.github/workflows/deploy-yolo.yml`
- `yolo-service/Dockerfile`

### Change env/config definitions

Start with:

- `backend/app/core/config.py`
- `yolo-service/app/config.py`

## 16. Bottom line

The deployment layer is built around one strong idea:

split the system into runtime-appropriate services, containerize each one cleanly, and let GitHub Actions plus Cloud Run manage repeatable releases.
