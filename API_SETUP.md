# OceanGuard AI — Gemini API Setup

**Status: Ready for your real Gemini key.** This document covers the Gemini Developer API key path for the 4 backend agents (narrator, briefing, patrol, ask). If you want the Google Cloud / Vertex-style Gemini path instead, use [GCP_GEMINI_SETUP.md](/d:/PROJECTS/AI_ML/OceanEye/GCP_GEMINI_SETUP.md).

---

## Project status check

Current verified state:

| Part | Check | Result |
|---|---|---|
| ML | `python -m pytest tests -q` | 20 passed, 2 skipped |
| Backend | `python -m pytest tests -q` | passes after Gemini migration |
| Frontend | `npx tsc --noEmit` | no errors |
| Frontend | `npm run build` | succeeds |

The backend agent runtime now targets the Gemini SDK via `google-genai`, while preserving the same fallback behavior and route contracts used by the frontend.

---

## How credentials are read

`backend/app/core/config.py` uses `pydantic-settings` with `env_file=".env"`, so it reads a file named `.env` from the current working directory of the backend process. There are two supported paths:

| Run method | Where the key goes | Why |
|---|---|---|
| Local dev (`cd backend && uvicorn app.main:app`) | `backend/.env` | The backend starts with `backend/` as its working directory |
| Docker (`docker-compose up`) | repo-root `.env` | `docker-compose.yml` reads root `.env` values and passes them into the container as real environment variables |

For this API-key path, both run methods use these variables:

```text
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
AGENT_MAX_TOOL_ROUNDS=5
AGENT_NARRATOR_MAX_TOKENS=500
AGENT_BRIEFING_MAX_TOKENS=400
AGENT_PATROL_MAX_TOKENS=600
AGENT_ASK_MAX_TOKENS=700
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

Get a Gemini key from:

`https://aistudio.google.com/apikey`

This path is simpler than the previously considered Vertex setup because it does not require a Google Cloud project just to get started.

---

## Setup steps

### 1. One-time backend environment

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2A. Local dev

```powershell
cd backend
copy .env.example .env
notepad .env   # set GEMINI_API_KEY=...
```

### 2B. Docker

```powershell
copy .env.example .env
notepad .env   # set GEMINI_API_KEY=...
docker-compose up --build
```

---

## Verify it is live

Run:

```powershell
curl http://localhost:8000/agents/status
```

Before a key is set, the expected shape is:

```json
{
  "provider": "gemini",
  "provider_mode": "api_key",
  "provider_enabled": false,
  "provider_importable": true,
  "client_ready": false,
  "fallback_mode": true,
  "model": "gemini-3.5-flash",
  "agent_max_tool_rounds": 5,
  "agent_narrator_max_tokens": 500,
  "agent_briefing_max_tokens": 400,
  "agent_patrol_max_tokens": 600,
  "agent_ask_max_tokens": 700
}
```

After a valid key is set, expect:

```json
{
  "provider": "gemini",
  "provider_mode": "api_key",
  "provider_enabled": true,
  "provider_importable": true,
  "client_ready": true,
  "fallback_mode": false
}
```

`fallback_mode: false` means the backend successfully constructed a Gemini client. If a later request fails upstream, each agent still catches that failure and falls back gracefully for the request.

For a quick live check after `/agents/status`:

```powershell
curl -X POST http://localhost:8000/agents/narrate/bar-reef-003
```

and

```powershell
curl -X POST http://localhost:8000/agents/ask -H "Content-Type: application/json" -d "{\"question\":\"Which detection is highest risk?\"}"
```

The first should return non-template narrative text, and the second should exercise the Gemini tool-calling loop.

---

## What changes once the key is live

| Agent | Route | Fallback today | With key |
|---|---|---|---|
| Narrator | `POST /agents/narrate`, `/agents/narrate/{id}` | Template sentence built from event fields | Gemini-written explanation with the same `why_flagged` and `uncertainty` response shape |
| Briefing | `POST /agents/briefing`, `/agents/briefing/current` | Template summary naming the highest-risk event | Gemini-written situation briefing |
| Patrol | `POST /agents/patrol`, `/agents/patrol/current` | Deterministic risk-first ranking | Gemini-ranked list with generated justifications |
| Ask | `POST /agents/ask` | Keyword-matched canned answers | Full tool-using agent loop over live repository data |

No frontend changes are needed. The route contracts are unchanged, so the UI simply renders whichever explanation text comes back.

---

## Model and config defaults

```text
GEMINI_MODEL=gemini-3.5-flash
AGENT_MAX_TOOL_ROUNDS=5
AGENT_NARRATOR_MAX_TOKENS=500
AGENT_BRIEFING_MAX_TOKENS=400
AGENT_PATROL_MAX_TOKENS=600
AGENT_ASK_MAX_TOKENS=700
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

All of these are read from `backend/app/core/config.py::Settings` and can be overridden in either `backend/.env` for local runs or repo-root `.env` for Docker.

---

## Cost note

Going live means real Gemini API calls. The main repeated-call paths are:

- `DailyBriefing` and `PatrolBoard`, which now only re-fetch when the underlying risk data changes
- `EvidenceCard`, which requests narration once per selected vessel

That keeps costs predictable, but each live agent request is still billable once a real key is configured.
