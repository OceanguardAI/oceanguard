# OceanGuard AI — Plan Consistency Audit & Corrections

**Audit date:** 2026-06-16
**Branch audited:** `main`
**Scope:** Full read-only consistency check across every planning/documentation file in the repo, cross-referenced against the actual code files that already exist.

**Files checked:**
`README.md`, `BUILD_PLAN.md`, `CONTRIBUTING.md`, `docs/architecture.md`, `docs/data-dictionary.md`, `docs/responsible-ai.md`, `PLAN_ML_PIPELINE.md`, `PLAN_BACKEND_AGENTS.md`, `PLAN_FRONTEND.md`, `ml/pipeline/risk.py`, `ml/requirements.txt`, `backend/requirements.txt`, `.gitignore`.

**Overall result: the repo is in good shape.** Out of 12 audited categories, 8 are fully consistent. 4 minor issues were found — none affect the demo path or the data values teams rely on. No corrections are needed to the GFW detection data, the risk formula, the RiskEvent schema, the API routes, the model metrics, or the MPA polygon — these are byte-for-byte consistent across every file that repeats them.

---

## Summary Table

| # | Category | Status |
|---|---|---|
| 1 | Risk formula (weights, AIS/MPA score logic, thresholds) | ✅ Consistent |
| 2 | GFW detection data (bar-reef-001 → 004) | ✅ Consistent |
| 3 | RiskEvent schema fields (Pydantic / TypeScript / data-dictionary) | ⚠️ 1 minor issue |
| 4 | API route tables (BUILD_PLAN / backend plan / frontend plan) | ✅ Consistent |
| 5 | Model metrics (mAP50, precision, recall, scene ID, detection count) | ✅ Consistent |
| 6 | MPA polygon / WDPA coordinates | ✅ Consistent |
| 7 | Port / marina data | ✅ Consistent |
| 8 | requirements.txt vs actual files | ⚠️ Issue found (backend only) |
| 9 | .gitignore coverage of generated/large artifacts | ✅ Consistent |
| 10 | Internal contradictions within a single file | ⚠️ Issue found |
| 11 | Cross-file references (data files each plan expects to exist) | ✅ Consistent |
| 12 | Build-order dependency clarity | ⚠️ Minor gap |

---

## Corrections Needed

### 1. `PLAN_BACKEND_AGENTS.md` — requirements.txt version pins don't match the real file

**Where:** `PLAN_BACKEND_AGENTS.md`, Step 1 (`requirements.txt` block)
**What's wrong:** The plan lists newer version constraints than what's actually committed in `backend/requirements.txt`:

| Package | Plan says | Actual file says |
|---|---|---|
| fastapi | `>=0.111.0` | `>=0.110.0` |
| uvicorn[standard] | `>=0.29.0` | `>=0.27.0` |
| pydantic-settings | `>=2.2.0` | `>=2.0.0` |
| anthropic | `>=0.28.0` | `>=0.25.0` |
| pydantic | `>=2.7.0` (extra line) | not present as a separate line |

**Fix:** Update the `requirements.txt` code block in `PLAN_BACKEND_AGENTS.md` Step 1 to match `backend/requirements.txt` exactly (8 lines, versions as shown in the "Actual file says" column above). **Owner: Team 2 (Backend + Agents).**

**Not an issue:** `ml/requirements.txt` matches `PLAN_ML_PIPELINE.md`'s listed requirements exactly — no action needed there.

---

### 2. `docs/data-dictionary.md` — contradicts itself on risk_level thresholds

**Where:** `docs/data-dictionary.md`, line ~51 (field table) vs lines ~91-95 (§Risk Engine formula section) — same file.
**What's wrong:** Line 51 describes the enum as:
```
LOW (<0.35) / MEDIUM (0.35–0.55) / HIGH (0.55–0.75) / CRITICAL (≥0.75)
```
This range notation is ambiguous about which level owns the boundary value (e.g. is exactly 0.55 MEDIUM or HIGH?). Just 40 lines later, the same file's own Risk Engine section states the correct, unambiguous rule that matches `ml/pipeline/risk.py` exactly:
```
CRITICAL  if risk_score ≥ 0.75
HIGH      if risk_score ≥ 0.55
MEDIUM    if risk_score ≥ 0.35
LOW       otherwise
```
**Fix:** Update line 51 to read: `` `LOW` (<0.35) / `MEDIUM` (≥0.35) / `HIGH` (≥0.55) / `CRITICAL` (≥0.75). `` so both sections of the file agree. **Owner: whoever maintains `docs/` (no single team — flag for the doc owner).**

---

### 3. `PLAN_BACKEND_AGENTS.md` — `image_quality` typed as plain `str` instead of documented enum

**Where:** `PLAN_BACKEND_AGENTS.md`, `RiskEvent` Pydantic schema (Step 3), field `image_quality: str`
**What's wrong:** `docs/data-dictionary.md` documents `image_quality` as an enum (`"Good" | "Degraded" | "Poor"`), but the Pydantic schema in the backend plan types it as an unconstrained `str`. Functionally harmless — FastAPI/Pydantic will accept any string — but it means the backend won't reject an invalid value the way the data dictionary implies it should.
**Fix (optional, low priority):** Change to `image_quality: Literal["Good", "Degraded", "Poor"]` in `PLAN_BACKEND_AGENTS.md` if strict validation is wanted. **Owner: Team 2 (Backend + Agents).** Not blocking — safe to leave as-is for the demo.

---

### 4. `BUILD_PLAN.md` — Build Order section doesn't spell out the cross-team dependency explicitly

**Where:** `BUILD_PLAN.md`, "Build Order" section
**What's wrong:** The numbered build order (risk.py → build_risk_events.py → copy to backend/data/ → backend app → ... ) is correct, but it doesn't explicitly say in words that **Team 2 (Backend) cannot run its tests or start its server until Team 3 (ML) has delivered `risk_events.json` into `backend/data/`**. The dependency is correctly implied by the ordering and is stated inside `PLAN_BACKEND_AGENTS.md` and `PLAN_ML_PIPELINE.md` themselves, just not called out as a named cross-team blocker in the master `BUILD_PLAN.md`.
**Fix (optional, low priority):** Add one sentence to the Build Order section: "Team 2 cannot start backend tests until Team 3 delivers `risk_events.json` + `bar_reef.geojson` into `backend/data/`." **Owner: whoever maintains `BUILD_PLAN.md`.** Not blocking — each team plan file already states its own dependency correctly.

---

## Verified Consistent (no action needed)

- **GFW detection data** — all 4 records (bar-reef-001 through 004: lat, lon, distance to MPA, near_mpa flag, risk_score, risk_level) are identical across `BUILD_PLAN.md`, `docs/data-dictionary.md`, `PLAN_ML_PIPELINE.md`, `PLAN_BACKEND_AGENTS.md`, and `PLAN_FRONTEND.md`. The headline detection bar-reef-003 (8.51°N 79.68°E, 0.4 km from MPA, score 0.61, HIGH) is correct everywhere it appears.
- **Risk formula** — weights (0.30/0.25/0.25/0.10/0.10), AIS score logic (0.0/0.3/1.0), and MPA score logic (1.0/0.6/0.0) match `ml/pipeline/risk.py` exactly in every doc that reproduces the formula.
- **RiskEvent schema** — all 24 fields, names, and optionality match across `docs/data-dictionary.md`, the Pydantic model in `PLAN_BACKEND_AGENTS.md`, and the TypeScript interface in `PLAN_FRONTEND.md` (aside from issue #3 above).
- **API routes** — every route in `BUILD_PLAN.md`'s route table is implemented identically in `PLAN_BACKEND_AGENTS.md` and consumed identically in `PLAN_FRONTEND.md`'s API quick reference.
- **Model metrics** — mAP50 0.838, precision 0.830, recall 0.818, dataset "HRSID (2857 train / 715 val)", 122 detections, scene ID `590dd08f71056cacv` all match across `BUILD_PLAN.md`, `docs/data-dictionary.md`, `PLAN_ML_PIPELINE.md`, and the `metrics.json` content in `PLAN_BACKEND_AGENTS.md`.
- **MPA polygon** — Bar Reef WDPA coordinates are identical in `BUILD_PLAN.md`, `docs/data-dictionary.md`, and `PLAN_ML_PIPELINE.md`; correctly converted from `[lon, lat]` GeoJSON order to `[lat, lon]` Leaflet order in `PLAN_FRONTEND.md`'s `MapView.tsx`.
- **Port/marina data** — Marina at (8.2155202, 79.7061466), ~33 km from bar-reef-003, consistent everywhere it's referenced.
- **.gitignore** — correctly excludes `best.pt`, `ml/data/`, `ml/outputs/detections_scene1_georef.json`, `ml/outputs/risk_events.json`, `node_modules/`, `frontend/dist/`, `__pycache__/`, `.env`.
- **Cross-file data references** — every data file a plan expects to exist in `backend/data/` (`risk_events.json`, `bar_reef.geojson`, `metrics.json`, `ports.json`) is specified to be created/copied by exactly one of the three team plans — no orphan references, no missing specs.

---

## Recommended Next Action

None of the 4 issues above block the demo or any team's work. Suggested priority if anyone wants to clean these up:
1. Fix #1 (requirements.txt versions) — quick, prevents confusion if someone pins exact versions from the plan.
2. Fix #2 (data-dictionary self-contradiction) — quick, improves doc trustworthiness.
3. Fix #3 and #4 are cosmetic and can be skipped without consequence.
