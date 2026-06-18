# OceanGuard AI — Gemini Migration Handoff

**Status: IN PROGRESS — core code done, docs/tests/config cleanup remaining.** This is a handoff doc for whichever agent/session picks this up next. The user decided (after considering direct Anthropic API and Claude-via-Vertex-AI) to run the 4 backend agents on **Google's Gemini API** instead of Claude. The core agent code has been rewritten; several supporting files still need the same treatment, and one file (`backend/tests/test_endpoints.py`) is **mid-edit**.

**⚠️ Conflict warning:** While this migration was in progress, something else in this session/repo independently edited `.env.example` (root), `backend/README.md`, `README.md`, and `docker-compose.yml` — but in the **Anthropic** direction (adding `ANTHROPIC_MODEL`, more `AGENT_*` env passthroughs, etc.), apparently unaware of the Gemini decision. **Those edits need to be overwritten/redone for Gemini, not merged with.** Run `git diff` on those 4 files before touching them to see exactly what's there now.

---

## What's already done (verified pattern, not yet test-verified end-to-end)

| File | Status |
|---|---|
| `backend/requirements.txt` | ✅ `anthropic>=0.25.0` → `google-genai>=0.1.0` |
| `backend/app/core/config.py` | ✅ `anthropic_api_key`/`anthropic_model` → `gemini_api_key`/`gemini_model` (default `"gemini-3.5-flash"`) |
| `backend/app/agents/client.py` | ✅ Fully rewritten: `genai_importable()` + `get_client()` returning `genai.Client(api_key=...)`, same staleness-guard caching pattern as before |
| `backend/app/agents/helpers.py` | ✅ `first_text_block()` replaced with `extract_text(response)` — safely reads `response.text`, returns `""` on any exception (Gemini raises if a response has no text parts, e.g. function-call-only responses) |
| `backend/app/agents/narrator.py` | ✅ Uses `client.models.generate_content(model=settings.gemini_model, contents=..., config=types.GenerateContentConfig(system_instruction=..., max_output_tokens=...))`, reads `extract_text(response)` |
| `backend/app/agents/briefing.py` | ✅ Same pattern as narrator |
| `backend/app/agents/patrol.py` | ✅ Same pattern as narrator |
| `backend/app/agents/ask.py` | ✅ Full rewrite — `TOOLS` now use `"parameters"` key (was `"input_schema"` for Claude) wrapped in `types.Tool(function_declarations=TOOLS)`; tool loop reads `response.candidates[0].content.parts[i].function_call` (`.name`, `.args`, `.id`) instead of Claude `tool_use` blocks; sends results back via `types.Part.from_function_response(name=..., response={"result": ...}, id=...)` appended as `types.Content(role="user", parts=[...])`. `_run_tool()` itself is untouched (provider-agnostic). All imports of `google.genai.types` are **local/lazy** inside each `try:` block — never at module top-level — so the app still works in deterministic-fallback mode even if `google-genai` isn't installed at all (mirrors how `anthropic` was never imported at module level before). |
| `backend/app/models/schemas.py` | ✅ `AgentStatus` fields renamed provider-neutral: `anthropic_enabled→provider_enabled`, `anthropic_importable→provider_importable`, `anthropic_model→model`, plus new `provider: str` field (`"gemini"`) |
| `backend/app/api/routes/agents.py` | ✅ `/agents/status` handler updated to populate the renamed fields, imports `genai_importable` instead of `anthropic_importable` |
| `backend/tests/test_agents.py` | ✅ Fully rewritten — `_FakeClient` now exposes `.models.generate_content(...)` instead of `.messages.create(...)`; all response fakes use `SimpleNamespace(text=...)` or `SimpleNamespace(candidates=[...])` matching Gemini's shape; the tool-loop test (`test_ask_tool_loop_executes_tool_and_returns_final_answer`) builds a fake `function_call` namespace and asserts against `calls[1]["contents"][-1].parts[0].function_response.response["result"]` — **this specific attribute path (`.function_response`) is inferred from SDK naming symmetry with `.function_call` and has NOT been empirically verified against the real `google-genai` package yet** (see Verification section below — fix this first if the test fails). |
| `backend/tests/test_endpoints.py` | ⚠️ **PARTIALLY DONE** — only one `patch("app.core.config.settings.anthropic_api_key", "")` → `patch("app.core.config.settings.gemini_api_key", "")` has been fixed so far. **`test_agent_status_without_api_key` (around line 215-230) still references the OLD field names and is now broken** — see exact fix needed below. |

## What's NOT done yet — do these in order

### 1. Finish `backend/tests/test_endpoints.py`

Find `test_agent_status_without_api_key` (currently still asserting on `anthropic_enabled`/`anthropic_importable`/`anthropic_model`) and replace it with:

```python
def test_agent_status_without_api_key(client: TestClient) -> None:
    response = client.get("/agents/status")
    assert response.status_code == 200
    body = response.json()
    from app.agents.client import genai_importable

    assert body["provider"] == "gemini"
    assert body["provider_enabled"] is False
    assert body["provider_importable"] is genai_importable()
    assert body["client_ready"] is False
    assert body["fallback_mode"] is True
    assert body["model"] == "gemini-3.5-flash"
    assert body["agent_max_tool_rounds"] == 5
    assert body["agent_narrator_max_tokens"] == 500
    assert body["agent_briefing_max_tokens"] == 400
    assert body["agent_patrol_max_tokens"] == 600
    assert body["agent_ask_max_tokens"] == 700
```

Then `grep -n "anthropic" backend/tests/test_endpoints.py` to confirm nothing else is left (there shouldn't be — the fixture-level patch was already fixed).

### 2. `backend/.env.example` — rewrite for Gemini

Replace the `ANTHROPIC_API_KEY` block with:

```
# Copy this file to backend/.env and fill in your real key.
# Without a key, every agent route still works via deterministic fallback logic.

GEMINI_API_KEY=
# Get one at https://aistudio.google.com/apikey

# Optional overrides (defaults shown — usually no need to change these)
# GEMINI_MODEL=gemini-3.5-flash
# AGENT_MAX_TOOL_ROUNDS=5
# AGENT_NARRATOR_MAX_TOKENS=500
# AGENT_BRIEFING_MAX_TOKENS=400
# AGENT_PATROL_MAX_TOKENS=600
# AGENT_ASK_MAX_TOKENS=700
# CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 3. Root `.env.example` — **undo the concurrent Anthropic edit, redo for Gemini**

Someone just expanded this file with `ANTHROPIC_MODEL`/`AGENT_*` vars (see `git diff .env.example` — added today, in the Anthropic direction). Replace the whole "agent" section with the same `GEMINI_API_KEY` + optional overrides block as backend/.env.example above. Keep whatever non-agent content (if any) was already there before that concurrent edit.

### 4. `docker-compose.yml` — same conflict, same fix

Someone just added an `environment:` block passing through `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, and the `AGENT_*` vars (see `git diff docker-compose.yml`). Change the env var **names** to the Gemini equivalents:

```yaml
environment:
  GEMINI_API_KEY: ${GEMINI_API_KEY:-}
  GEMINI_MODEL: ${GEMINI_MODEL:-gemini-3.5-flash}
  AGENT_MAX_TOOL_ROUNDS: ${AGENT_MAX_TOOL_ROUNDS:-5}
  AGENT_NARRATOR_MAX_TOKENS: ${AGENT_NARRATOR_MAX_TOKENS:-500}
  AGENT_BRIEFING_MAX_TOKENS: ${AGENT_BRIEFING_MAX_TOKENS:-400}
  AGENT_PATROL_MAX_TOKENS: ${AGENT_PATROL_MAX_TOKENS:-600}
  AGENT_ASK_MAX_TOKENS: ${AGENT_ASK_MAX_TOKENS:-700}
  CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:5173,http://localhost:3000}
```

### 5. `backend/README.md` — same conflict pattern

Someone just added a "copy .env.example to .env" snippet and an `/agents/status` curl check — both fine to keep, just change `ANTHROPIC_API_KEY=sk-ant-...` to `GEMINI_API_KEY=...` in the example, and change the prose "Claude-backed agents" (line ~8) to "Gemini-backed agents". Also update the "Ask agent fallback topics" section's "Without Anthropic" phrase (~line 130) to "Without a Gemini key".

### 6. `API_SETUP.md` (repo root) — full rewrite

This file is currently 100% Anthropic-oriented (key location, `/agents/status` example JSON with old field names, model defaults table). Rewrite it analogous to its current structure but for Gemini:
- Where the key goes: `backend/.env` for local dev (`GEMINI_API_KEY=...`), repo-root `.env` for Docker.
- `/agents/status` example JSON — use the NEW field names: `provider`, `provider_enabled`, `provider_importable`, `client_ready`, `fallback_mode`, `model`, plus the `agent_*_max_tokens` fields (unchanged names).
- Where to get a key: `https://aistudio.google.com/apikey` (free tier available, no GCP project required — much simpler than the Vertex AI path that was considered and dropped).
- Keep the "what changes once the key is live" table and the cost note — both still apply, just say "Gemini API calls" instead of "Anthropic API calls".

### 7. Root `README.md`

Only one line was added by the concurrent edit (a pointer to `API_SETUP.md`) — that line is fine as-is, no provider-specific wording in it. No change needed here beyond what `API_SETUP.md` itself says.

### 8. Optional / lower-priority doc cleanup

These files mention Anthropic/Claude but are historical planning docs, not runtime-affecting — fine to leave, or do a final pass once everything above is verified working:
`CODE_REVIEW_FINDINGS.md`, `CORRECTIONS.md`, `PLAN_BACKEND_AGENTS.md`, `CONTRIBUTING.md`, `docs/responsible-ai.md`, `docs/architecture.md`, `BUILD_PLAN.md`.

### 9. Install + verify

```powershell
cd backend
.\.venv\Scripts\activate
pip uninstall anthropic -y   # remove the old dependency
pip install -r requirements.txt   # installs google-genai
python -m pytest tests -q
```

**If `test_ask_tool_loop_executes_tool_and_returns_final_answer` fails on the `.function_response` attribute access** (flagged as unverified above): inspect the real `types.Part.from_function_response(...)` return value in a `python -c` one-liner —

```powershell
python -c "from google.genai import types; p = types.Part.from_function_response(name='x', response={'result':'y'}, id='1'); print(p)"
```

— and fix the attribute name in the test (and re-check it isn't also assumed anywhere in `ask.py` itself, though `ask.py` never reads that attribute back, only constructs it, so `ask.py` is likely fine regardless).

Then, with a real key:

```powershell
copy .env.example .env
notepad .env   # set GEMINI_API_KEY=... (from https://aistudio.google.com/apikey)
uvicorn app.main:app --reload
curl http://localhost:8000/agents/status
```

Expect `"provider":"gemini","provider_enabled":true,"client_ready":true,"fallback_mode":false`. Then `POST /agents/narrate/bar-reef-003` and confirm live Gemini text (not the templated fallback sentence), and `POST /agents/ask` with `{"question":"Which detection is highest risk?"}` to exercise the real function-calling loop end to end.

### 10. Frontend

No frontend changes are expected or needed — the `/agents/*` route contracts are unchanged. Worth one manual click-through of the demo path (map → bar-reef-003 → "Get AI Explanation" → Patrol Board → Ask OceanGuard) against a live-keyed backend once everything above passes, just to confirm nothing in the response shape drifted.

---

## Reference: the verified Gemini SDK facts this migration is built on

(Verified live against `ai.google.dev` during planning, not from training-data memory.)

- Package: `google-genai` (current unified SDK, not the deprecated `google-generativeai`). `pip install -U google-genai`.
- Client: `from google import genai; client = genai.Client(api_key=...)`. Reads `GEMINI_API_KEY` or `GOOGLE_API_KEY` from env automatically if no explicit key passed (`GOOGLE_API_KEY` wins if both set) — this project passes the key explicitly via `settings.gemini_api_key`, so that auto-detection doesn't matter here, just noted for completeness.
- Call: `client.models.generate_content(model="gemini-3.5-flash", contents=..., config=types.GenerateContentConfig(system_instruction=..., max_output_tokens=N))` → `.text`.
- Function calling: declare `{"name","description","parameters"}` dicts wrapped in `types.Tool(function_declarations=[...])`; read `response.candidates[0].content.parts[i].function_call` (`.name`/`.args`/`.id`); reply via `types.Part.from_function_response(name=..., response={...}, id=...)`.
- Model ID confirmed from docs: `gemini-3.5-flash`. **No distinct higher-capability "pro" tier ID was confirmed during research** — if the user wants a more capable model than flash, check `https://ai.google.dev/gemini-api/docs/models` for the current lineup before picking an ID.
