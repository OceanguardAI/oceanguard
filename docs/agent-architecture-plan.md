# Agent architecture plan

Written October 2, 2026. This extends the plan's "evidence-grounded explanations"
into a bounded set of agents that do more work while staying auditable. The code
facts below were read from the repository on that date.

## 1. Current state

| Agent | File | What it does today | Limits found |
|---|---|---|---|
| Narrator | `backend/app/agents/narrator.py` | One Gemini call per case, JSON `{why_flagged, uncertainty}`, template fallback | Sees only the event's own fields; no citations back to evidence |
| Briefing | `briefing.py` | One call, three plain sentences, template fallback | Until this review nothing detected a response cut off by the token limit (fixed, see section 6) |
| Patrol | `patrol.py` | One call ranks up to 20 cases, deterministic-sort fallback | The LLM is asked to rank; ranking should be deterministic with the LLM only explaining |
| Ask | `ask.py` | Tool loop (5 tools, up to 5 rounds) over the case repository | Tools see sample case records only; cannot see GFW activity cells, source health, associations, alerts or tracks |
| (unused) | `services/gemini_agent.py` | Nothing imports it | Dead code; remove |

Cross-cutting problems:

- **Hand-written knowledge drifts.** The Ask system prompt described the scoring
  formula, and that text was wrong twice (it contradicted the docs, then the code
  changed so live ingestion stopped producing scored events at all). It has been
  corrected and `backend/tests/test_agent_knowledge.py` now ties the stated
  thresholds to the seed data, but the durable fix is to generate such text from
  code and data (section 5).
- **No evaluation.** There is no measure of whether an agent's statements are
  supported by the evidence it was given.
- **No observability.** Calls, tools used, tokens, latency and failures are not
  recorded.
- **Model settings are inconsistent.** `config.py` defaults to `gemini-2.5-flash`;
  the previous compose file defaulted to `gemini-3.5-flash`. Both were listed
  without a shutdown date on Google's deprecations page when checked on
  2026-10-02, so this is a consistency problem, not an outage risk. Pin one id.
- **Vertex-only production config.** The backend workflow forced Vertex AI mode.
  Without a Google Cloud project the client already supports an API key
  (`GEMINI_API_KEY`); the env templates now default to that.

## 2. Principles

1. **Deterministic core decides; agents retrieve, explain and challenge.** An agent
   never changes a score, identity, association state or review status.
2. **Every factual statement cites evidence ids** that exist in the tool results of
   the same run. Unsupported statements are removed or the answer abstains.
3. **Abstention is a valid answer.** "Unavailable", "ambiguous" and "I cannot tell
   from the loaded data" must be reachable and rewarded in evaluation.
4. **Structured output, validated.** Pydantic models for every agent output; a
   failed parse falls back to a deterministic template.
5. **Free text from data sources is untrusted.** Vessel names, MMSI-linked text and
   provider strings are attacker-influenceable (see section 7).
6. **Provider-neutral.** Works with an API key or Vertex; all agents keep a
   no-model fallback so the demo works offline.
7. **Bounded cost.** Per-run token and tool-round limits, caching by
   `(agent, input hash)`, and rate-limit-aware retries.

## 3. Agent roster

Each agent is a narrow function with a typed contract, not a free-roaming
autonomous loop. "Depends on" refers to the stages in the
[development plan](end-to-end-development-plan.md).

| ID | Agent | Inputs and tools | Output | Depends on |
|---|---|---|---|---|
| A1 | **Ask v2** (grounded retrieval) | Tools for case records, GFW activity cells (bbox/time), source health, associations, alerts, tracks, model metrics, dataset versions | Answer plus `evidence_ids`; `abstained: true` when data is absent | B, C |
| A2 | **Provenance sentinel** | `/sources/status`, ingest status, requested vs resolved GFW dataset version, data age | A data-trust banner and a list of reasons; flags version change (v4 to v5), stale or sample-only data | A2 stage (version pinning) |
| A3 | **Skeptic** (challenge agent) | One case plus its evidence | `benign_explanations`, `missing_evidence`, `recommended_checks`; never a verdict | I |
| A4 | **Association explainer** | `association.py` decision, candidate list, rejection reasons | Plain-language explanation of why a state is `matched`/`ambiguous`/`unmatched`/`unavailable`; cannot alter the state | H |
| A5 | **Scene planner** | Area and time, Copernicus catalogue query (deterministic) | Which Sentinel-1 acquisitions exist, revisit expectation, coverage gaps; explicit "no coverage" | E |
| A6 | **Patrol planner** | Deterministic ranking and route (see section 4) | Ranked list with route and a short justification per item | I |
| A7 | **Case-file writer** | Case, tracks, associations, reviews, versions | Evidence export (timeline, sources, model and dataset versions), summary text only | I |
| A8 | **Review-feedback analyst** (offline) | Analyst decisions over time | Per-rule and per-agent precision, drift report; proposes, never applies, changes | I, K |

The existing Narrator and Briefing become thin consumers of A1/A2/A3 outputs
rather than separate prompt silos.

## 4. Patrol planning: where RL does and does not belong

Choosing which detections to visit within fuel and time limits is a Team
Orienteering Problem. A classical optimiser (for example Google OR-Tools) solves
the static version near-optimally, deterministically and explainably, which suits
this project's auditability goal. Reinforcement learning is only justified for the
dynamic version (moving vessels, new detections arriving mid-patrol, weather,
several boats), and it would be trained entirely in a simulator because the system
holds no patrol-boat telemetry or vessel tracks. So the roadmap is: nearest-first
baseline, then OR-Tools, then an optional PPO study that must be reported as
simulation-only, with the comparison itself as the research output. The LLM stays
out of route decisions and only explains the chosen plan.

## 5. Grounding and knowledge management

- **Generated knowledge.** Build the "how OceanGuard works" text from code
  constants and data files (score weights and thresholds, near-MPA radius, dataset
  version, model metrics) instead of hand-editing prose. Tests compare the
  rendered text to the source values.
- **Tool coverage matches the data model.** Tools for activity cells, observations,
  tracks and alerts so the agent stops reasoning only over sample cases.
- **Evidence ids.** Every tool result carries stable ids (case id, observation id,
  activity-cell id, source id, dataset version). Prompts require citing them.
- **Mechanical citation verifier.** After generation, extract ids and numbers from
  the answer and check each against the run's tool outputs. Drop or flag anything
  unmatched; if too little remains, abstain.
- **Deterministic fallbacks remain** for every agent and are what runs with no key.

## 6. Reliability work already done and next

Done on October 2, 2026:

- `hit_token_limit` and `trim_to_last_sentence` in `backend/app/agents/helpers.py`,
  used by Briefing and Ask: a response stopped by the token budget is trimmed to
  complete sentences or replaced by the deterministic answer. Tests in
  `backend/tests/test_agent_truncation.py`.
- Ask knowledge corrected to the current data model with drift tests.

Next (small, in order):

1. Confirm in the current SDK documentation whether thinking tokens count against
   `max_output_tokens` for the chosen model, then set an explicit thinking
   configuration for these short tasks so the visible text is not starved.
2. Pin one model id for demos and run a manual and automated check of all four
   agents after any change.
3. Delete `services/gemini_agent.py`.
4. Add per-run logging of agent, model, tool calls, token counts, latency and
   fallback reason to a bounded table or log stream.

## 7. Threat model specific to agents

Free text that flows from external feeds into prompts is an injection route. AIS
vessel names, destinations and any provider description fields are set by the
vessel operator or a third party. Required mitigations:

- Put external text inside clearly delimited data blocks and state in the system
  prompt that it is data, never instructions.
- Strip control characters and cap field lengths before prompting.
- Tool arguments must never be copied from data fields without validation
  (ids must match known patterns and exist).
- No agent has write tools. Mutations (reviews, alerts) go through authenticated,
  audited API routes that a human triggers.
- Test with planted instructions in vessel-name fields and require that outputs
  neither follow them nor leak the system prompt.

## 8. Evaluation (research content)

Build a labelled question set, about 100 items, in four groups: answerable from
loaded data, unanswerable (no such data), ambiguous, and adversarial (injected
instructions, requests to accuse or to state intent). Measure:

| Metric | Definition |
|---|---|
| Unsupported-claim rate | Fraction of identifiers and numbers in answers not present in that run's tool results |
| Abstention precision/recall | Whether the agent declines exactly when the data cannot answer |
| Injection success rate | Fraction of adversarial items where planted instructions change behaviour |
| Accusation rate | Fraction of answers asserting wrongdoing or intent |
| Cost and latency | Tokens and seconds per answer at p50/p95 |
| Analyst usefulness | Blinded rating by a small panel on a fixed rubric |

Compare: the current Ask; tools without a verifier; tools with the verifier and
abstention; and at least two model choices. Report confidence intervals and
publish the question set. This supports research question RQ5 in the
[literature review](literature-review.md), where related maritime LLM work
(AIS-LLM, VTS-LLM) was found to focus on AIS-only data and Text-to-SQL rather than
SAR evidence with verified citations.

## 9. Delivery order and acceptance gates

| Step | Deliverable | Gate |
|---|---|---|
| 1 | Reliability items in section 6, model pinned | Agent tests green; truncation tests green; manual check of all four agents on the pinned model |
| 2 | Ask v2 tools and evidence ids | Every tool result carries ids; Ask answers cite them in a sample of 20 questions |
| 3 | Citation verifier and abstention | Unsupported-claim rate measured on the question set, and lower than step 2 without the verifier |
| 4 | A2 provenance sentinel | Shows requested and resolved dataset version and data age in the UI |
| 5 | A3 skeptic and A4 explainer | No accusatory language in the adversarial set; states never altered |
| 6 | A5 scene planner and A6 patrol planner | OR-Tools plan beats nearest-first on stated metrics in simulation |
| 7 | Evaluation harness and write-up | Question set, scripts and results reproducible from the repository |

Do not describe any agent as "autonomous"; every one is advisory, bounded and
reviewable.
