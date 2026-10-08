# OceanGuard AI — Presentation Brief

Plain-language answers to: *what is happening, what is live, why these datasets, what are the limits, and how would this become a real operational system for Sri Lanka / India.*

Facts below come from this repo (code and `backend/data/*.json`). Items marked **(verify)** are external facts (prices, revisit times, agency data access) that must be checked before being said on stage.

---

## 1. The whole flow in one picture

```
 (A) LIVE, free                    (B) ON-CLICK, live                 (C) SAMPLE, pre-made
 Global Fishing Watch API          User clicks map / draws area       backend/data/risk_events.json
 "SAR vessel presence" per         → backend asks Sentinel Hub        126 stored events
 grid cell, last N days            for a Sentinel-1 radar chip        (122 from ONE xView3 scene,
        │                          → YOLO service finds ships          4 hand-made "GFW" samples)
        ▼                                  │                                  │
 cyan circles on the map           red/teal contact markers            coloured risk dots + KPIs,
 ("activity cells")                (unconfirmed radar leads)           briefing, patrol, Ask agent
```

Three different things appear on the map. They are **not** the same kind of data:

| What you see | Where it comes from | Live? | What it means |
|---|---|---|---|
| **Cyan circles** | GFW 4Wings report, dataset `public-global-sar-presence:v4.0` (`backend/app/services/gfw_ingest.py`) | **Yes** (GFW refreshes it; there is a processing delay) | "Radar satellites saw N vessels in this grid cell in this period." An aggregate count, **not** an individual ship, no risk score. |
| **Red / teal contact markers** | You click *Verify* or *Sweep*; Sentinel-1 chip fetched on demand, YOLO run on it (`backend/app/api/routes/verify.py`, `yolo-service/app/main.py`) | **Yes** (latest available Sentinel-1 pass, not "now") | A model-detected bright blob that looks like a ship. A **lead for a human**, not a confirmed vessel. Red = no stored observation nearby; teal = near a stored one. |
| **Coloured risk dots (green/amber/red)** | `backend/data/risk_events.json`, loaded into memory (no database) | **No — sample/seed data** | 122 detections from a single 15 Jan 2024 xView3 scene plus 4 illustrative cases. Risk scores here were **pre-computed offline**. |

> One-sentence honest summary: **the activity circles and the YOLO checks use live public data; the risk-scored dots, KPIs, briefing and patrol board run on stored sample data.**

---

## 2. Why SAR? Why GFW? Why HRSID?

### Why SAR (radar) and not normal satellite photos
- Dark vessels switch off AIS, so you cannot find them with transponder data. You need a sensor that sees the ship itself.
- SAR sends its own microwaves: works **at night and through cloud** (the monsoon seas around Sri Lanka are often cloudy). Metal hulls reflect strongly, so ships show as bright points on dark sea.
- Weakness: it shows a bright dot, not a photo. It cannot read a name, flag, or cargo, and it confuses ships with rocks, platforms, wave clutter and ghost echoes.

### Why Global Fishing Watch (GFW)
- Free API for non-commercial use, global coverage, no need for us to download and process terabytes of Sentinel-1.
- GFW already runs vessel detection on Sentinel-1 worldwide and matches detections against AIS, so it gives "vessel presence in this area" for free.
- Limits: returns **aggregated cells**, has a processing lag, is not real-time, and the dataset version changes (`latest` becomes v5 on **21 Oct 2026**; we pin `:v4.0`). Terms are for non-commercial use **(verify before any commercial/government deployment)**.

### Why HRSID (and why that is a weakness we can explain)
- HRSID is a **free, public, already-labelled** ship-detection dataset. It let us build a working detector quickly with the compute we had.
- But it is high-resolution SAR (about 0.5–3 m pixels, mostly Chinese coastal and port scenes). Our live source, Sentinel-1, has about **10 m pixels** (roughly 20 × 22 m resolution). A 20 m fishing boat is ~2 pixels wide in Sentinel-1 and ~10+ pixels in HRSID.
- So: **trained on one kind of image, deployed on another.** That is called *domain shift*. We did not hide it; we measured it (Section 4).

---

## 3. What does a YOLO capture actually identify?

When the user clicks *Verify* or sweeps an area:
1. Backend requests a Sentinel-1 VV chip around that point from Copernicus (Sentinel Hub API).
2. The chip goes to the YOLO11n service (`/detect-point`), which returns boxes + confidence + the chip image.
3. Each box = "something shaped and bright like a ship here".

It **does not** identify: ship name, flag, type, cargo, intent, or whether it is fishing, smuggling or lawful. It also cannot say whether the ship is "dark" unless an AIS check is added (currently not wired). It can be wrong in both directions (false alarms on clutter; misses on small boats).

Correct wording on stage: **"YOLO produces candidate radar contacts for a human analyst to review."**

---

## 4. Are we using live data? Why not fully?

### What is live today
| Component | Live? |
|---|---|
| GFW SAR activity cells | Yes (delayed by GFW processing) |
| Sentinel-1 chips for YOLO | Yes, but "latest pass", can be days old |
| MPA polygons (WDPA via ArcGIS) | Static reference data (updated by the provider occasionally) |
| Risk-scored events, KPIs, briefing, patrol, Ask | Sample data (126 stored events) |
| AIS cross-match ("is this ship broadcasting?") | **Not running** (removed; marked as sample in the data) |

### Why it is not fully live — the honest reasons
1. **Free Sentinel-1 is not real-time.** It passes over a given sea area only every few days **(verify revisit for Sri Lanka)** and data appears hours after the pass. It is good for patterns and leads, not for chasing a boat in progress.
2. **Real-time vessel identity needs AIS, and good AIS costs money.** Free options exist (terrestrial/community AIS, GFW's processed AIS) but give patchy coverage far offshore; satellite AIS (Spire, Kpler/MarineTraffic, Orbcomm, etc.) is a paid subscription **(verify pricing)**.
3. **High-resolution / rapid-revisit SAR is commercial and tasked.** ICEYE, Capella, Umbra, Planet-class providers sell tasking/archive per scene or by subscription **(verify pricing, quote-based)**. Copernicus Contributing Missions (CCM) is free only for approved users, with quotas.
4. **Student/free-tier infrastructure.** No GPU quota, no managed database, in-memory store, single-region Azure student subscription.
5. **Scoring was deliberately removed from the live path** rather than shown with made-up inputs (commit `8f07b9e`), because the AIS cross-match and agreement logic were not actually running.

So the defensible statement is: *"Everything marked live uses free public feeds. The step that would make it a true operational system — frequent high-resolution SAR plus satellite AIS — is a paid data layer that this prototype does not buy."*

---

## 5. Training: what we did, with the resource story told honestly

| Stage | Data | Compute | Result |
|---|---|---|---|
| 1. Baseline | HRSID (2,857 train / 715 val) | Colab-class GPU, 50 epochs | mAP@50 = 0.838 **on HRSID's own test split** |
| 2. Reality check (A0) | xView3 validation: real Sentinel-1, 3 scenes, 930 vessels | Azure ML CPU (`cpu-eval`) | **Recall only 30.9%**; 5% for 15–30 m ships, 9.5% for 30–60 m, 65% for ≥120 m |
| 3. Fine-tune (runs B–E) | small xView3 train subset + HRSID replay | Azure ML **CPU only** (student quota: 0 GPU) | Run E accepted: recall **42.2%**, 15–30 m **25%**, 30–60 m **43.7%**, HRSID mAP drop 0.007 (gate ≤ 0.02). Runs B–D rejected (HRSID drop > 0.02) |

### Why we did not train only on Sentinel-1
- Labelled Sentinel-1 ship data exists (xView3), but the full set is ~1.3 TB train; we have a laptop with ~10 GB free disk, no GPU, and an Azure student subscription with zero GPU quota.
- So we used the resource-appropriate path: (a) baseline on the free dataset we could afford, (b) **measure** the gap on real Sentinel-1, (c) fine-tune on the largest xView3 slice CPU-training could handle, (d) accept a model only if it passes a regression gate.
- "Trained on dataset A, used on dataset B" is stated openly, with the measured cost (30.9% → 42.2% recall), rather than hidden behind the 0.838 number.

### Training limitations to state
- Fine-tune used few scenes (small sample → wide confidence intervals, e.g. 15–30 m: 25%, 95% CI 14–40%).
- No 0–15 m ships exist in the evaluation scenes → **no measurement at all for the smallest boats.**
- False positives rose 0.37 → 0.92 per 100 km² for the recall gain.
- `finetuned_runE.pt` is committed but **the deployed service still defaults to `best.pt`** until switched via `MODEL_PATH`.
- Pixel-size mismatch is reduced, not removed; preprocessing (dB vs linear scaling, chip size, overlap) is not yet unified between training and serving.

---

## 6. The risk score: pre-made vs live

**Today:** the scores in `risk_events.json` were calculated offline (`ml/risk.py`, weighted formula) for the sample events. The live GFW path yields cells with **no** score. (There are two different formulas in the project history — see `docs/PROJECT_CONTEXT.md`.)

**How to make it genuinely live** (design, not yet built):

```
New detection (GFW cell drill-down / YOLO contact / commercial SAR)
   │
   ├─ 1. AIS association: any AIS position within ±N min and ±R km?   → matched / unmatched / unknown (no AIS coverage)
   ├─ 2. Zone features:  inside MPA? inside EEZ? distance to maritime boundary? distance to port/coast
   ├─ 3. Behaviour:      loitering, speed, heading vs lane, AIS gap before/after, rendezvous with another vessel
   ├─ 4. Size estimate:  from SAR extent (rough, ±)
   └─ 5. Score = transparent weighted sum (shown to the user) → LOW/MED/HIGH + "why flagged" list
```

Rules to keep it defensible:
- Show the **reasons**, not just a number. Do not call it a probability until it is calibrated against labelled outcomes (e.g. past boardings/seizures).
- "AIS unknown" (no coverage) must be distinct from "AIS absent" (coverage but silent). Dark ≠ missing data.
- Output is a **priority queue for human review**, never an accusation.

---

## 7. Making it a real tool for Sri Lanka / India

### 7.1 Use cases and what the data can / cannot do

| Use case | What SAR + AIS can do | What it cannot do | Extra data needed |
|---|---|---|---|
| **Illegal fishing across the maritime boundary (e.g. Palk Bay / Gulf of Mannar)** | Count vessels near the boundary, flag unmatched radar contacts, trend over time, flag entries into protected areas | Detect many small wooden boats (often under ~20 m **(verify typical sizes)**) reliably at 10 m resolution; prove nationality or that fishing occurred | Authoritative boundary geometry from the official source (do not hand-draw), satellite AIS, patrol reports, fishing-vessel registry/transponder data (government-held) |
| **Marine protected areas** (e.g. Bar Reef, already in the demo; Gulf of Mannar) | Show vessels inside MPAs with a time history | Prove violation of MPA rules | Park rules, ranger reports |
| **Sea border security / unidentified vessels** | Wide-area "unmatched contact" awareness, change detection | Identify the vessel or its intent | Coastal radar, patrol aircraft/vessels, naval intelligence feeds |
| **Drug / contraband vessels** | Spot **anomalies that cue other assets**: unmatched large or small contacts in remote water, loitering, rendezvous between two vessels, AIS going dark mid-route, drifting/stationary mother-ship patterns | Detect or identify drugs or cargo. Radar cannot distinguish a smuggler from an innocent fishing boat. Intent cannot be inferred from imagery. | Intelligence tips, vessel history, tasking of high-res SAR/optical + patrol assets on the cued area; legal process |

Framing for this use case: **OceanGuard is a cueing layer ("where should the Navy / Coast Guard look first?"), not a detection-of-crime system.** The decision to board always stays with the authority.

### 7.2 What a real deployment needs (and roughly what it costs in kind)

| Layer | Prototype today | Operational version |
|---|---|---|
| SAR | Free Sentinel-1 (days, 10 m) | + commercial tasked SAR for cued areas (ICEYE/Capella/Umbra-type), **paid** |
| AIS | GFW-processed, partial | Satellite + terrestrial AIS feed, **paid**; government coastal AIS receivers |
| Vessel registry / VMS | None | Fishing-vessel transponder/VMS data from Department of Fisheries / Coast Guard (access by agreement, not purchasable) |
| Optical | None | Sentinel-2 (free, daytime, cloud-limited) or commercial for ID imagery |
| Model | HRSID + small xView3 fine-tune, CPU | Train on full xView3 + local labelled Sri Lankan/Indian scenes on GPU; per-size thresholds |
| Storage | In-memory seed JSON | PostGIS (code already exists in `store/operational.py`), object storage for chips, scheduler |
| Compute | CPU, scales-to-zero | GPU endpoint or batch inference per scene |
| Security | Open endpoints | API auth, audit log, role-based access, data-sharing agreements |
| People | Student team | Analyst workflow, legal review, agency MoU |

### 7.3 Phased plan (resource-honest)

| Phase | Scope | Needs | Outcome |
|---|---|---|---|
| **P0 (now)** | Truthful prototype: live GFW cells + on-click YOLO, sample cases labelled, v4.0 pinned | Free keys | Demo + research results |
| **P1** | Region focus (Sri Lanka–India waters): ingest Sentinel-1 for the region on a schedule, run `finetuned_runE.pt`, store observations in PostGIS | Small cloud budget, GPU or longer CPU batch | Own detections, not just GFW cells |
| **P2** | Live scoring pipeline (Section 6), AIS association with whatever feed is affordable; **measure** false alarms against GFW/AIS-matched ground truth | AIS subscription or agency data | Defensible, explainable risk queue |
| **P3** | Commercial SAR tasking on cued areas; small-boat model trained on local labels | Paid SAR + labelling effort | Small-vessel capability |
| **P4** | Agency integration: boundary/MPA authoritative layers, VMS fusion, alert workflow, audit | MoU with Navy / Coast Guard / Fisheries Dept. | Operational decision support |

---

## 8. Limitations (say these before they are asked)

1. **Not real-time.** Free Sentinel-1 = days between looks; GFW has processing delay.
2. **Dashboard risk data is sample data.** 122 of 126 events come from a single 2024 scene; scores are pre-computed; 4 "GFW" cases are illustrative.
3. **No AIS cross-match is running**, so "dark" cannot currently be confirmed by the system.
4. **Small boats are the weak point** — exactly the vessels most relevant to artisanal fishing and smuggling. Measured recall on 15–30 m ships is 25% (CI 14–40%); 0–15 m unmeasured.
5. **Domain shift.** Trained largely on HRSID (0.5–3 m), applied to 10 m Sentinel-1. Partly fixed by a small xView3 fine-tune; not eliminated.
6. **Small evaluation set** (3 scenes, 930 vessels) → wide confidence intervals; no generalisation claim to the Indian Ocean (xView3 scenes are not Sri Lankan waters).
7. **YOLO detects, it does not identify.** No type, flag, intent or cargo.
8. **False positives** (0.92 / 100 km² after fine-tune) need human review.
9. **No database, no auth.** Mutation/costly endpoints are open; fine for a demo, not for deployment.
10. **GFW terms and version drift.** Non-commercial terms; `latest` flips to v5 on 21 Oct 2026 (pinned to v4.0).
11. **Legal/ethical.** Outputs are leads for human review; maritime-boundary and enforcement decisions belong to the competent authority.

---

## 9. Scope statement for the presentation

**We claim:**
- A working pipeline that combines free live radar-derived vessel presence (GFW), on-demand Sentinel-1 retrieval, an ML detector, MPA spatial context and explainable AI agents.
- A *measured* evaluation on real Sentinel-1 with confidence intervals, an honest baseline (30.9%), and a gated improvement (42.2%).
- A design and phased plan to extend it to live scoring and regional use.

**We do not claim:**
- Real-time tracking, live dark-vessel scoring, confirmed illegal activity, vessel identification, drug detection, or readiness for operational enforcement.
- Accuracy on Sri Lankan / Indian waters (not yet measured there).

---

## 10. Likely questions and short answers

| Question | Answer |
|---|---|
| Why HRSID if you use Sentinel-1? | It is the free labelled SAR ship dataset we could train with our resources; the mismatch is real, so we measured it on xView3 (30.9% recall) and fine-tuned (42.2%). |
| Why not train on Sentinel-1 directly? | The labelled Sentinel-1 dataset is ~1.3 TB; we had a laptop with limited disk and an Azure student account with zero GPU quota. We used a small subset on CPU. |
| Is it live? | GFW cells and Sentinel-1 checks use live public sources (delayed). Risk-scored dots are sample data. |
| Why not truly live? | Real-time needs paid satellite AIS and tasked high-resolution SAR; free Sentinel-1 revisits every few days. |
| What are the dots? | Cyan = GFW aggregated vessel presence per cell. Red/teal = YOLO radar leads from an on-click check. Green/amber/red = stored sample cases. |
| Is the risk score real? | For sample cases it is a pre-computed transparent formula. The live pipeline is designed (Section 6) but not built; it needs AIS data. |
| Can it catch drug boats? | It can cue attention to anomalies (unmatched contacts, loitering, rendezvous, AIS gaps). It cannot see cargo or intent; authorities must follow up. |
| Can it detect small fishing boats? | Weakly: 25% recall for 15–30 m, unmeasured below that. Commercial high-res SAR is the fix. |
| What would it take to be operational? | Paid SAR + AIS, agency data (VMS, boundaries), GPU training on local labels, a database/auth, and an agency partnership. |
| What is new/research value? | GFW v4 vs v5 comparison, size-binned recall with confidence intervals on real Sentinel-1, domain-shift mitigation under constrained compute, and evaluated tool-calling agents. |

---

*Related: `docs/PROJECT_CONTEXT.md` (current state, pending work), `docs/SYSTEM_DEEP_DIVE.md` (code-level architecture), `ml/notebooks/training_runs_analysis.ipynb` (training evidence).*
