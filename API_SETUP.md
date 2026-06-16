# OceanGuard AI — Agent API Setup

**Status: ✅ Verified working, ready for your real key.** This document covers the one thing left before the 4 Claude agents (narrator, briefing, patrol, ask) go from deterministic-fallback mode to live AI mode: adding `ANTHROPIC_API_KEY`.

---

## Project status check (all 3 parts)

Re-verified just now, fresh:

| Part | Check | Result |
|---|---|---|
| ML | `python run_full_ml_workflow.py` | 126 events (4 GFW + 122 YOLO_SAR), `bar-reef-003` = 0.61/HIGH, no fallback data used |
| ML | `python -m pytest tests -q` | 20 passed, 2 skipped (optional `pyproj`/`rasterio` deps not installed locally) |
| Backend | `python -m pytest tests -q` (fresh venv, real deps) | 50 passed |
| Backend | `GET /health` | `{"status":"ok","events_loaded":126}` |
| Frontend | `npx tsc --noEmit` | no errors |
| Frontend | `npm run build` | succeeds |

One real gap found and fixed during this check: **the backend had never actually had its own virtual environment with `anthropic` installed** — tests were passing against a different Python environment that didn't have the `anthropic` package, so `anthropic_importable` would have been `False` even with a real key set. Created `backend/.venv`, installed `backend/requirements.txt` into it, confirmed `anthropic` (v0.109.2) imports cleanly. This is now a one-time fix — see Setup below.

---

## How the key is read

`backend/app/core/config.py` uses `pydantic-settings` with `env_file=".env"` — meaning it looks for a file named `.env` **in the current working directory the backend process is started from**. There are two separate paths depending on how you run it:

| Run method | Where the key goes | Why |
|---|---|---|
| Local dev (`cd backend && uvicorn app.main:app`) | `backend/.env` | cwd is `backend/` when uvicorn starts |
| Docker (`docker-compose up`) | repo-root `.env` | `docker-compose.yml` reads `${ANTHROPIC_API_KEY}` from the root `.env` and injects it as a container environment variable — pydantic-settings reads real env vars before the `.env` file, so the container needs no `.env` file of its own |

Both paths read the exact same variable name: `ANTHROPIC_API_KEY`.

---

## Setup steps

### 1. One-time backend venv (already done, documented for repeatability)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2A. Local dev — add your key

```powershell
cd backend
copy .env.example .env
notepad .env   # set ANTHROPIC_API_KEY=sk-ant-...
```

### 2B. Docker — add your key

```powershell
copy .env.example .env      # repo root
notepad .env                # set ANTHROPIC_API_KEY=sk-ant-...
docker-compose up --build
```

### 3. Verify it's live

```powershell
curl http://localhost:8000/agents/status
```

**Before a key is set** (verified just now):
```json
{"anthropic_enabled":false,"anthropic_importable":true,"client_ready":false,"fallback_mode":true,
 "anthropic_model":"claude-opus-4-8","agent_max_tool_rounds":5,
 "agent_narrator_max_tokens":500,"agent_briefing_max_tokens":400,
 "agent_patrol_max_tokens":600,"agent_ask_max_tokens":700}
```

**After a key is set** (verified just now with a placeholder key, to confirm the wiring — not a real call):
```json
{"anthropic_enabled":true,"anthropic_importable":true,"client_ready":true,"fallback_mode":false, ...}
```

`fallback_mode: false` means agent calls will now actually go to the Anthropic API instead of using the deterministic fallback text. If the key is invalid/expired, each agent's own `try/except` still catches the API error per-request and falls back gracefully — `fallback_mode` in `/agents/status` only reflects whether a client was *constructed*, not whether the last call succeeded.

---

## What changes once the key is live

| Agent | Route | Fallback today | With key |
|---|---|---|---|
| Narrator | `POST /agents/narrate`, `/agents/narrate/{id}` | Template sentence built from event fields | Claude-written explanation, same structure (`why_flagged`, `uncertainty`) |
| Briefing | `POST /agents/briefing`, `/agents/briefing/current` | Template summary naming the highest-risk event | Claude-written situation briefing |
| Patrol | `POST /agents/patrol`, `/agents/patrol/current` | Deterministic sort (risk_score → inside_mpa → near_mpa → distance) | Claude-ranked list (same sort priorities, requested in the prompt) with Claude-written justifications |
| Ask | `POST /agents/ask` | Keyword-matched canned answers | Full agentic tool-use loop — Claude can call `query_detections`/`get_event`/`get_risk_summary` tools against the live repository and answer freely |

No frontend changes are needed either way — the frontend never knows or cares whether a request was served by Claude or by fallback logic; it just renders whatever `why_flagged`/`briefing`/`justification`/`answer` text comes back.

---

## Model & config defaults (already set, override only if you want to)

```
ANTHROPIC_MODEL=claude-opus-4-8        # latest, most capable Claude model
AGENT_MAX_TOOL_ROUNDS=5                # caps the ask-agent's tool-use loop
AGENT_NARRATOR_MAX_TOKENS=500
AGENT_BRIEFING_MAX_TOKENS=400
AGENT_PATROL_MAX_TOKENS=600
AGENT_ASK_MAX_TOKENS=700
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

All of these are read from `backend/app/core/config.py::Settings` and can be overridden by adding the matching uppercase variable to your `.env` (see `backend/.env.example`).

---

## Cost note

Going live means real Anthropic API calls. The two components most likely to fire repeatedly:
- `DailyBriefing`/`PatrolBoard` on the frontend now only re-fetch when the actual risk data changes (fixed in the earlier code review pass), not on every UI interaction — so no surprise per-click cost there.
- `EvidenceCard`'s narrator call fires once per vessel selected — normal, expected usage.

No code change is needed for cost control beyond what's already in place; just be aware every map-marker click and review action that hits an agent route is now a billed call once the key is live.
