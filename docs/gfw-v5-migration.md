# Global Fishing Watch data pipeline v5: migration runbook

Written October 2, 2026, the day GFW emailed API users (summarised below).
Everything under "What GFW has said" comes from that email; everything under
"What OceanGuard uses" was read from this repository.

## What GFW has said

- Data Pipeline v5 becomes the default for requests using the `latest` alias on
  **21 October 2026**.
- From 2 October v5 can be previewed by naming it explicitly, for example
  `public-global-sar-presence:v5.0`. During the preview `latest` still returns v4.
  The preview is "near-final": monthly identity updates are still being merged
  before the official release.
- After 21 October `:v4.0` remains available but **receives no further updates**,
  and v3 datasets are deprecated.
- Stated changes (all described in AIS terms): more conservative apparent-fishing
  estimates with fewer and shorter events; the `discrepancy` vessel type removed
  and `insufficient_data` introduced, with more vessels in the broad `FISHING`
  class; more than 5,000 anchorages added and distance-from-port, distance-from-shore
  and bathymetry layers rebuilt, which may affect port visits, encounters and
  distance-based filters.
- GFW said full details would be published in October. The public release-notes page
  had no v5 entry when read on 2 October, so nothing beyond the email is known.
  Specifically, it is **not stated** whether `public-global-sar-presence` changes
  its schema or counts.

## What OceanGuard uses

| Item | Where | Exposure to v5 |
|---|---|---|
| SAR vessel presence report (`/v3/4wings/report`) | `backend/app/services/gfw_ingest.py` | Direct. Counts, cell occupancy and timestamps could differ |
| Dataset id | Was hard-coded `public-global-sar-presence:latest` | The alias silently changes on 21 October |
| Fields read | `lat`, `lon`, `detections`, `entryTimestamp`, optional ids | Low risk unless the schema changes; unknown until tested |
| AIS-side products (fishing effort, events, vessel identity) | Not used | None |
| Protected-area distances | Our own WDPA data and Shapely index | None; independent of GFW's rebuilt layers |
| Port distances | Our own OpenStreetMap list | None |

Conclusion: expected exposure is limited to the SAR activity layer's counts and
availability, but that is an expectation, not a measurement. Measure it.

## Code changes made

- `GFW_SAR_DATASET` setting, default pinned to `public-global-sar-presence:v4.0` so the
  21 October alias flip cannot change live data silently. Move to `...:v5.0` deliberately
  after the comparison below.
- The dataset GFW actually served (the key of each grouped result) is now stored on
  every activity cell, so a row can always be attributed to v4 or v5 even if the
  alias was requested. Record ids include that dataset, so the same cell from two
  versions can never collapse into one record.
- `/ingest/status` reports `requested_dataset`.
- `app/tools/compare_gfw_versions.py` compares two versions over a fixed window.
- Tests: `backend/tests/test_gfw_dataset_version.py`, `test_compare_gfw_versions.py`.

## Decision rule

| If the demo or evaluation happens | Set `GFW_SAR_DATASET` to | Why |
|---|---|---|
| Before 21 October | `public-global-sar-presence:v4.0` | Nothing changes mid-judging, and v4 is still updated |
| After 21 October | `public-global-sar-presence:v5.0` after the comparison below | v4 stops updating, so a rolling 7-day window would go stale |
| Any time results must be reproducible | An explicit version, never `latest` | The alias changes underneath you |

Show the dataset version on screen (planned in the provenance sentinel, agent A2),
and quote it in any figure, table or paper.

## Comparison runbook (do before 21 October)

1. Put a valid `GFW_API_TOKEN` in `backend/.env`.
2. Pick fixed windows that ended at least a week ago so both versions have fully
   processed them, for example one 30-day window and one different season, over the
   Bar Reef region and over a large reference region.
3. Run, per window:

   ```bash
   cd backend
   .venv/Scripts/python.exe -m app.tools.compare_gfw_versions \
       --start 2026-08-01 --end 2026-08-31 --bbox 79.4,8.0,79.9,8.8 \
       --out gfw_v4_vs_v5_barreef_aug.json
   ```

4. Read the report: cell Jaccard (overlap of occupied cells), detection ratio
   `b/a`, mean absolute count difference and Pearson correlation on shared cells,
   top-50 cell overlap, and totals split into inside-MPA, near-MPA and open water.
5. Decide the acceptance tolerance **before reading the numbers** (for example, the
   largest difference you would accept without changing any statement the interface
   makes). Record the decision with the data.
6. If differences are large, check whether they concentrate near protected areas
   (the context split) and whether they match GFW's published v5 notes once those
   appear. Do not attribute a difference to a cause GFW has not stated.
7. Keep the JSON reports. They are the data for research question RQ1 in the
   [literature review](literature-review.md).

The tool makes two live API calls with your token and respects GFW report limits
(date range at most one year). It was unit-tested on synthetic data only; it has
not been run against the live API.

## Status (2026-10-06) — 15 days until flip

- ✅ `GFW_SAR_DATASET` pinned to `public-global-sar-presence:v4.0` in `config.py`
  and `gfw_ingest.py`. The alias flip on 21 October will not affect us silently.
- ✅ Resolved dataset stored on every `ActivityAggregate` record.
- ✅ `/ingest/status` reports `requested_dataset`.
- ⚠️ **Comparison runbook NOT yet run.** Requires a valid `GFW_API_TOKEN` in
  `backend/.env`. This is the RQ1 research dataset — run before 21 Oct.
- ⚠️ GFW release notes for v5 still not published as of today.

## After 21 October

- Re-read the GFW release notes for the v5 entry and update this document with what
  they say.
- Run the comparison runbook (above) on a window ending before the flip so both
  versions have the same data.
- Switch `GFW_SAR_DATASET` to `public-global-sar-presence:v5.0` only after the
  comparison and only if differences are within your stated tolerance.
- Confirm `/ingest/status` shows the version you intend and the dashboard still
  loads activity cells.
- Treat any change in `ActivityAggregate.dataset` over time as a provenance event:
  do not merge v4 and v5 cells into one trend without saying so.
- GFW said v3 datasets will be deprecated. This project does not use them, but check
  any notebooks or scripts you wrote outside the repository.
