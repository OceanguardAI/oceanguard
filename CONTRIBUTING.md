# Contributing to OceanGuard AI

Thank you for your interest in contributing. This document explains how to set up the development environment and the conventions we follow.

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker + docker-compose (optional but recommended)
- An Anthropic API key (for agent features; system degrades gracefully without one)

### Local Setup

```bash
git clone <repo-url>
cd oceanguard-ai

# Python environment (backend + ML)
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r backend/requirements.txt
pip install -r ml/requirements.txt

# Node environment (frontend)
cd frontend && npm install && cd ..

# Environment variables
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY
```

### Generate the risk events data

Before running the backend, generate the data file:

```bash
# Place the artifact files first (see README.md for paths)
cd ml
python build_risk_events.py
cp outputs/risk_events.json ../backend/data/
```

### Run the stack

**With Docker (recommended):**
```bash
docker-compose up
```

**Without Docker:**
```bash
# Terminal 1
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

---

## Project Structure

See [BUILD_PLAN.md](BUILD_PLAN.md) for the full directory layout and implementation specs.

See [docs/architecture.md](docs/architecture.md) for system design decisions.

---

## Conventions

### Python (backend + ML)
- Python 3.11+, type hints throughout
- Pydantic v2 for all data models
- `ruff` for linting (if configured), else standard PEP 8
- No wildcard imports
- Functions in `pipeline/` are pure where possible (no side effects beyond file I/O)
- The risk formula in `risk.py` must not be changed without updating `docs/data-dictionary.md` and the unit test in `backend/tests/test_risk.py`

### TypeScript (frontend)
- Strict mode enabled
- All API responses typed via `src/types/index.ts`
- No `any` types
- Components receive typed props, no prop drilling beyond 2 levels

### Agents (Anthropic SDK)
- Model: `claude-opus-4-8`
- Every agent must have a deterministic fallback — the demo must work without an API key
- Agent prompts must reinforce decision-support framing: no accusations, always note uncertainty
- Tool schemas must be typed with `input_schema`

### Commits
- Conventional commits format: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- One logical change per commit
- Tests pass before pushing

---

## Testing

### Backend unit tests

```bash
cd backend
pytest tests/ -v
```

Key tests:
- `tests/test_risk.py` — risk engine formula verification (the §4 worked example must always pass)
- `tests/test_endpoints.py` — API route tests with httpx

### Frontend (manual for now)
Run `npm run dev` and verify the critical demo path:
1. Map loads with Bar Reef MPA polygon and 4 markers
2. Click bar-reef-003 → Evidence Card opens, score = 0.61 / HIGH
3. "Get AI Explanation" button returns narrator text
4. Patrol Board ranks bar-reef-003 first

---

## Adding a New Data Source

1. Cache the API response in `ml/data/`
2. Add an enrichment function in `ml/pipeline/enrich.py`
3. Update `build_risk_events.py` to incorporate the new data
4. Update `docs/data-dictionary.md` with the new field
5. Add the field to `backend/app/models/schemas.py`
6. Update the frontend `EvidenceCard.tsx` to display the new field

---

## Risk Engine Changes

The risk formula in `ml/pipeline/risk.py` is the auditable core of the system. Any change requires:

1. Update the formula in `risk.py`
2. Update `docs/data-dictionary.md` (Weight Rationale table)
3. Update `BUILD_PLAN.md` (Risk Engine section)
4. Update the unit test in `backend/tests/test_risk.py` with new expected values
5. Update the worked example in the UI (Model Metrics page or Evidence Card)

Weight changes must be justified in the PR description with reference to conservation domain knowledge.

---

## Responsible AI

All contributions must maintain the responsible-AI principles in [docs/responsible-ai.md](docs/responsible-ai.md):

- The system is decision-support only — never autonomous enforcement
- The risk formula stays deterministic and auditable
- Uncertainty is always surfaced, never suppressed
- No personal data is collected or processed

---

## Questions

Open an issue on GitHub or review [BUILD_PLAN.md](BUILD_PLAN.md) for the full technical specification.
