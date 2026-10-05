# OceanGuard AI - Groq API Setup

The agents (Narrator, Briefing, Patrol, Ask) call Groq's OpenAI-compatible chat API.
Without a key every agent route still answers through deterministic fallbacks, so
the dashboard works offline.

## 1. Create a key

Create an API key at https://console.groq.com/keys. Never commit it or paste it into chat.

## 2. Configure

Local backend:

```powershell
cd backend
copy .env.example .env     # then set GROQ_API_KEY=...
```

Docker: put `GROQ_API_KEY` in the repo-root `.env`; `docker-compose.yml` forwards it.

Azure: `scripts/azure_deploy.ps1` reads `GROQ_API_KEY` from `backend/.env` and stores
it as a Container Apps secret (`groq-key`). Nothing is printed.

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | empty | Enables the LLM; empty means fallback mode |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Any Groq chat model with tool use |
| `GROQ_TIMEOUT_S` | `20` | Per-request timeout |

## 3. Verify

```powershell
curl http://localhost:8000/agents/status
```

Expect `"provider": "groq"`, `"client_ready": true` and `"fallback_mode": false`.
`provider_enabled: false` means the key is not loaded; `provider_importable: false`
means `pip install -r backend/requirements.txt` has not been run.

After changing `GROQ_MODEL`, run `backend/tests/test_agents.py` and try a briefing
and an Ask question manually.
