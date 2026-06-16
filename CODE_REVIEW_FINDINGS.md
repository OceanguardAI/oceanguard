# OceanGuard AI — Code Review Findings & Corrections

**Status: ✅ RESOLVED.** All findings below were fixed in commits `e00d096` ("Apply code review corrections"), `9b5b9f9` ("Fix docker runtime data wiring"), and one follow-up comment-only clarification in `ml/build_risk_events.py`. This document is kept as a record of what was found and how it was fixed — useful if similar bugs are reintroduced later.

**Audit date:** 2026-06-16 · **Resolution verified:** 2026-06-16
**Branch:** `feature/backend-agents`

**Verification at resolution time:**
```
cd backend && python -m pytest tests -q   →  50 passed
cd ml      && python -m pytest tests -q   →  20 passed, 2 skipped (pyproj/rasterio not installed locally — environment gap, not a code bug)
cd frontend && npx tsc --noEmit            →  no errors
cd frontend && npm run build               →  succeeds (only a non-blocking "chunk >500kB" advisory, no errors)
```

---

## 🔴 Critical — all fixed

### 1. MPA polygon never rendered on the map — **FIXED**
[frontend/src/components/MapView.tsx](frontend/src/components/MapView.tsx) now branches on `geojson.type === "FeatureCollection"` and reads `features?.[0]?.geometry`, with a fallback to a bare `geometry` and a visible error banner if neither shape is present. `fetchMPA()` in [frontend/src/lib/api.ts](frontend/src/lib/api.ts) now returns a properly typed `MPAGeoJSON` union (`GeoJSONFeature | GeoJSONFeatureCollection`, defined in [frontend/src/types/index.ts](frontend/src/types/index.ts)) instead of `any`, so this class of shape mismatch is now a compile-time error, not a silent runtime no-op.

### 2. Non-atomic, unlocked `risk_events.json` writes — **FIXED**
[backend/app/store/repository.py](backend/app/store/repository.py) now guards `save()`/`update_review()` with an `RLock`, writes to a temp file in the same directory, `fsync`s, and atomically `os.replace()`s onto the real path. A crash mid-write can no longer corrupt the file, and concurrent review updates can no longer race.

### 3. Patrol tie-break treated `0.0 km` as `9999 km` — **FIXED**
[backend/app/agents/patrol.py:21](backend/app/agents/patrol.py#L21) now reads `event.distance_to_mpa_km if event.distance_to_mpa_km is not None else 9999` instead of the falsy-prone `... or 9999`.

---

## 🟠 High priority — all fixed

4. **Unguarded file reads in `/mpa`, `/ports`, `/model-metrics`** — Fixed. [geo.py](backend/app/api/routes/geo.py) now has a shared `_load_required_json()` helper that raises a clean `HTTPException(503, ...)` if the file is missing; [metrics.py](backend/app/api/routes/metrics.py) got the same existence check.
5. **`ask.py` tool crash on malformed input** — Fixed. [ask.py](backend/app/agents/ask.py) now uses `inputs.get("id")` with an explicit error string instead of a bare `inputs["id"]`, and the outer exception handler now logs (`print(f"Ask agent error: {exc}")`) instead of swallowing silently.
6. **No auth on review-status endpoint** — Deliberately deferred; flagged as a production-hardening item, not a demo blocker.
7. **Six frontend components had no error UI** — Fixed. `App.tsx`, `MapView.tsx`, `DailyBriefing.tsx`, `PatrolBoard.tsx`, `ModelMetrics.tsx`, and `EvidenceCard.tsx` all now have dedicated `error` state, a `.catch()` that sets it, and a visible message in the render path. Every fetch effect also added a `cancelled` flag to ignore stale resolutions.
8. **Race condition in `EvidenceCard`'s AI explanation** — Fixed. The `useEffect` now sets a `cancelled` flag in its cleanup function and checks it before calling `setNarrative`/`setError`/`setLoading`.
9. **Unintended extra AI-agent calls on every review click** — Fixed. `DailyBriefing.tsx` and `PatrolBoard.tsx` now depend on a derived `requestKey` string (`id:score:level:distance:inside:near` joined per event) instead of the `events` array reference, so a review-status update no longer re-triggers a briefing/patrol re-fetch unless the actual risk data changed.

---

## 🟡 Medium priority (ML data integrity) — all fixed

10. **Silent fallback to fake GFW demo data** — Fixed. `extract_gfw_entries()` now returns a `(entries, used_fallback)` tuple; `used_fallback_gfw_data` is threaded through `build_events()` → `run_full_ml_workflow.py`'s summary JSON → printed by `report_ml_status.py`, so a parsing failure is now machine-checkable instead of buried in stdout.
11. **`detect.py` key drift (`tile_path` vs `tile`)** — Fixed. `detect.py` and `bootstrap_demo_assets.py` both now emit `"tile"`, matching the real cached artifact.
12. **`fishing_score`/`repeated_activity_score` permanently dead weight** — Documented. Added inline comments at both `calculate_risk()` call sites in `build_risk_events.py` noting these are reserved for future GFW signals not yet wired up.
13. **`nearest_port_distance()` fabricated a port location on empty data** — Fixed. Now returns `(None, None)` instead of a hardcoded lat/lon; `ml/tests/test_enrich.py` has a new test (`test_nearest_port_distance_returns_none_when_port_data_is_empty`) covering this.

---

## 🟢 Low priority — addressed or deliberately deferred

- **Duplicated GFW-format-sniffing logic** — Fixed. `validate_artifacts.py` now imports and reuses `extract_gfw_entries()` from `build_risk_events.py` instead of duplicating the sniffing logic.
- **Duplicated 24-field required-fields list** — Fixed. `report_ml_status.py` now imports `RISK_EVENT_FIELDS` from `build_risk_events.py` instead of keeping its own copy.
- **`GET /agents/status` missing from `backend/README.md`** — Fixed, added to the endpoint table.
- **`test_optional_imports.py` was tautological and brittle** — Fixed. It now actually imports `georeference.py` via `importlib` and asserts `georeference_detections` exists, and uses an absolute path anchored to `Path(__file__)` instead of a cwd-relative literal, so it passes regardless of which directory pytest is invoked from.
- **`test_enrich.py` used wide, weak range assertions** — Fixed. Now asserts exact values via `pytest.approx` (e.g. `near_distance == pytest.approx(0.37, abs=0.02)`), matching the real computed values confirmed in `ml/outputs/ml_workflow_summary.json`.
- **Hardcoded placeholder timestamp on all 122 YOLO_SAR events** — Left as-is functionally (no real per-scene capture date is available in the cached data), but now has an explanatory comment in `build_risk_events.py` so it reads as an intentional placeholder, not an oversight.
- **`"Temprary"` typo in `ml/build_risk_events.py`'s `DEFAULT_SOURCE_ROOT` and related files/tests** — **Deliberately deferred.** It's load-bearing in multiple tests (`test_materialize_artifacts.py`, `test_run_full_ml_workflow.py`) and file paths; fixing it requires a coordinated rename across several files + tests for a purely cosmetic gain. Not worth the regression risk right now. Revisit if/when those files are touched for another reason.
- **`docker-compose.yml` mounted `backend/data` read-only** — Fixed (in `9b5b9f9`). Once review updates started persisting to disk (fix #2), the `:ro` mount would have made that persistence silently fail inside Docker. Changed to read-write, and `README.md` now documents that `backend/data` is the shared writable runtime directory.

---

## Confirmed correct (unchanged from original audit)

- `ml/pipeline/risk.py`'s risk formula — untouched, still matches the spec exactly.
- Backend `RiskEvent` schema ↔ frontend TypeScript `RiskEvent` interface — still a 1:1 field match.
- All 4 agent deterministic fallbacks — still correct with no `ANTHROPIC_API_KEY`.
- CORS — still scoped to an explicit allowlist, not wildcarded.
- `ResponsibleAIFooter` — still renders unconditionally on every page.
