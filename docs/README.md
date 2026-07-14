# OceanGuard AI Documentation

This folder is the reference set for understanding how OceanGuard AI is built.

If you want to learn the project after having developed it with agents, start here and move from top to bottom.

## Recommended reading order

1. `PROJECT_GUIDE.md`
2. `architecture.md`
3. `CODEBASE_MAP.md`
4. `modules/dashboard-and-interface.md`
5. `modules/live-ingestion-and-risk-scoring.md`
6. `modules/spatial-intelligence-and-protected-areas.md`
7. `live-sar-and-user-selection-flow.md`
8. `modules/agents-and-explanations.md`
9. `modules/ml-pipeline-and-models.md`
10. `modules/deployment-and-runtime.md`
11. `data-dictionary.md`
12. `responsible-ai.md`
13. `GCP_API_SETUP_CLI.md`

## What each document is for

### Core project references

- `PROJECT_GUIDE.md`
  - Best first read.
  - Explains what the product does, how the full request lifecycle works, and how the major features fit together.

- `architecture.md`
  - Top-level system architecture.
  - Shows the relationship between data sources, ML pipeline, backend, agents, and frontend.

- `CODEBASE_MAP.md`
  - Helps you find the correct file quickly.
  - Useful when you want to change a feature and need to know where it lives.

### Feature/module references

- `modules/dashboard-and-interface.md`
  - Frontend behavior, screen structure, state flow, map overlays, landing page, and mobile responsiveness.

- `modules/live-ingestion-and-risk-scoring.md`
  - How live detections enter the system, how they are transformed into `RiskEvent`s, and how scoring works.

- `modules/spatial-intelligence-and-protected-areas.md`
  - How MPAs are loaded, indexed, queried, and rendered.

- `live-sar-and-user-selection-flow.md`
  - Deep dive on live Sentinel-1 chips, point scan, area sweep, and the user-selection flow.

- `modules/agents-and-explanations.md`
  - Gemini integration, tool-calling, fallbacks, and how each agent works.

- `modules/ml-pipeline-and-models.md`
  - Offline ML workflow, artifacts, model validation, risk-event building, and backend handoff.

- `modules/deployment-and-runtime.md`
  - Docker, GitHub Actions, Cloud Run, runtime services, and environment configuration.

### Supporting references

- `data-dictionary.md`
  - Field-by-field meaning for the system's core data structures.

- `responsible-ai.md`
  - Safety posture and human-review boundaries.

- `GCP_API_SETUP_CLI.md`
  - Practical setup for GCP, GitHub Actions, and cloud secrets/runtime configuration.

## Best way to learn this repo

Use this sequence:

1. Read `PROJECT_GUIDE.md` to build the mental model.
2. Read `CODEBASE_MAP.md` so you know where each responsibility lives.
3. Pick one feature doc and keep the referenced code files open beside it.
4. Trace one end-to-end path:
   - frontend click
   - frontend API helper
   - backend route
   - backend service
   - stored response
   - UI render
5. Then move to the next feature.

## Most important idea

OceanGuard is not one monolithic AI feature.

It is a set of cooperating parts:

- a deterministic backend
- a spatial intelligence layer
- an on-demand SAR verification path
- a model-serving service
- AI explanation agents
- a frontend command console
- a deployment/runtime layer

Learning the project becomes much easier once you treat those as separate modules.
