# Agents and Explanations Module

## 1. What this module does

This module is the natural-language layer of OceanGuard.

Its job is not to replace the deterministic system.

Its job is to make the deterministic system understandable and easier to operate.

The main files are:

- `backend/app/api/routes/agents.py`
- `backend/app/agents/client.py`
- `backend/app/agents/narrator.py`
- `backend/app/agents/briefing.py`
- `backend/app/agents/patrol.py`
- `backend/app/agents/ask.py`
- `backend/app/agents/helpers.py`

## 2. The core philosophy

OceanGuard uses AI in a constrained role.

That role is:

- explain
- summarize
- prioritize
- answer questions

It does not:

- compute the main risk formula
- invent operational truth
- silently override backend state

This is a very important architecture decision.

It makes the product safer and easier to trust.

## 3. Provider wiring

The Gemini client logic lives in `backend/app/agents/client.py`.

It supports two provider modes:

- `api_key`
- `gcp`

Decision rule:

- if `GEMINI_USE_GCP` or `GOOGLE_GENAI_USE_VERTEXAI` is enabled, use GCP mode
- otherwise use API key mode

Current runtime inputs include:

- `GEMINI_API_KEY`
- `GEMINI_USE_GCP`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `GEMINI_MODEL`

This is useful because:

- local development can use API keys
- production can use GCP-native auth

## 4. Why the client is a singleton

`get_client()` caches the Gemini client instance using a signature built from:

- provider mode
- project or API key
- location

Why this is good:

- avoids repeated client construction
- reacts correctly if relevant settings change
- centralizes client readiness checks

## 5. The four main agents

### A. Narrator

Route:

- `POST /agents/narrate`
- `POST /agents/narrate/{event_id}`

File:

- `backend/app/agents/narrator.py`

Purpose:

- explain one detection

Outputs:

- `why_flagged`
- `uncertainty`

Important design detail:

The narrator is forced into plain text JSON output and then sanitized further.

Why:

- operational UI should not show random markdown artifacts
- explanation text should be consistent and predictable

### B. Briefing

Routes:

- `POST /agents/briefing`
- `POST /agents/briefing/current`

Purpose:

- summarize the current situation

This is the shift-start or big-picture agent.

### C. Patrol

Routes:

- `POST /agents/patrol`
- `POST /agents/patrol/current`

Purpose:

- rank likely patrol targets

This transforms raw detections into action ordering.

### D. Ask

Route:

- `POST /agents/ask`

Purpose:

- interactive assistant for live operational questions

This is the most advanced agent in the repo.

## 6. Why the Ask agent is special

The ask agent is not just "send question to model, print answer."

It combines:

- embedded system knowledge
- live dataset snapshot
- tool declarations
- tool execution loop
- fallback logic

That makes it much more reliable than a plain prompt-only assistant.

## 7. How Ask works internally

The heart of the design is in `backend/app/agents/ask.py`.

### Layer 1. Static system knowledge

`SYSTEM_KNOWLEDGE` explains:

- what OceanGuard does
- data sources
- scoring logic
- YOLO verification
- dashboard meaning
- responsible use

This allows the assistant to answer system-explanation questions without hallucinating.

### Layer 2. Live dataset embedding

The system prompt is built with:

- dataset summary counts
- full current detection list
- risk level breakdown
- source breakdown

That means many questions can be answered directly from prompt context.

Examples:

- which event is highest risk?
- how many are near an MPA?
- how many are pending review?

### Layer 3. Tool declarations

Ask defines tools like:

- `query_detections`
- `get_event`
- `get_risk_summary`
- `get_model_metrics`
- `get_ports`

These are not frontend tools. They are backend-side data access tools for Gemini.

### Layer 4. Tool execution loop

The model can request tool calls.

The backend then:

1. executes the tool locally
2. returns result text back into the model conversation
3. lets Gemini produce the final answer

This is an important pattern because:

- the model stays language-focused
- the backend stays source-of-truth-focused

### Layer 5. Deterministic fallback

If Gemini is not available or errors out:

- the route still responds
- several common question classes still work

This is strong product design.

It means the assistant degrades gracefully instead of becoming dead UI.

## 8. Formatting discipline

Several agent files enforce plain-text output rules.

This is more important than it may seem.

Why:

- model output often drifts toward markdown
- dashboards look unprofessional when explanation text contains stray formatting
- stable rendering matters in operational tools

So the code explicitly strips:

- bold markers
- headings
- bullets in the wrong style
- leftover placeholder text

This is a good example of product-hardening around LLM behavior.

## 9. Relationship between agents and deterministic logic

The best way to understand this module is:

- deterministic system decides structure
- AI system explains and navigates that structure

Examples:

### Deterministic

- event score
- event level
- inside/near MPA
- review state
- current store contents

### Agent-powered

- Why does this event matter?
- What is the overall situation?
- Which patrol should I check first?
- Explain this product behavior in plain language

That separation is one of the biggest strengths of the architecture.

## 10. Why each agent exists as its own file

Splitting the agents is better than one giant prompt file because each task has different needs.

### Narrator

- structured output
- single-event focus

### Briefing

- many-event compression
- executive tone

### Patrol

- prioritization
- actionable ranking

### Ask

- free-form operator questions
- tool-backed retrieval

This separation keeps prompts and logic understandable.

## 11. Where agents pull data from

All agents ultimately depend on repo-backed data, especially the in-memory repository.

That means:

- they are grounded in current backend state
- they are not expected to know hidden state outside the application

This is another important learning point:

the AI layer is downstream of the operational dataset, not parallel to it.

## 12. If you want to modify this module

### Change provider/auth logic

Start with:

- `backend/app/agents/client.py`

### Change explanation tone or output shape

Start with:

- `backend/app/agents/narrator.py`

### Change assistant system knowledge

Start with:

- `backend/app/agents/ask.py`

### Add new assistant tools

Start with:

- `backend/app/agents/ask.py`
- `backend/app/store/repository.py`
- relevant API/data files

### Improve fallback behavior

Start with:

- `_fallback(...)` in `ask.py`
- equivalent fallback logic in narrator/briefing/patrol

## 13. Bottom line

This module makes OceanGuard explainable and operable.

Its best idea is not merely "use Gemini."

Its best idea is:

- keep the logic deterministic
- keep the AI grounded
- keep the UI readable
- keep the system usable even when the model is unavailable
