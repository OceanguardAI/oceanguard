# Small-vessel detection: analysis, validation protocol and plan

Written October 2, 2026. This document answers two questions: why does the
system miss small vessels, and how can anyone tell whether a fix is correct.

## 1. Status of the reported fix

A fix for missed small ships using OpenCV was reported, but **it is not in this
checkout**. What was checked on 2026-10-02:

- `main` was clean at commit `8a3ec6f` (only an untracked `gitleaks-report.json`).
- No tracked or git-ignored file under the repository mentions `cv2`, OpenCV, CFAR,
  `adaptiveThreshold` or connected-component analysis (the single "opencv" hit is a
  comment in `yolo-service/Dockerfile` about image-decoding libraries).
- The only stash (`codex-temp-before-feature-merge`, 15 June) changes two lines of
  `.env.example`.
- The other local and remote branches were last updated between 15 and 20 June,
  older than `main`.
- Both model weight files are unchanged since June (`ml/models/best.pt` is dated
  15 June, and the service copy was committed on 19 June), so no retrained detector
  exists here either.

So the fix could not be inspected and this document does not judge it. Section 5
gives a protocol that can, and section 6 gives an OpenCV-specific correctness
checklist. If the fix lives on another machine, notebook or branch, commit it (or
share it) and run the protocol.

## 1a. Measured baseline (run A0, 2026-10-04)

The current `ml/models/best.pt` was run on one xView3 validation scene crop
(scene `590dd08f71056cacv`, VH band, 8192 x 8192 px at 10 m, the window with the
most labelled vessels), on a CPU job in Azure ML. Confidence 0.25, match radius
30 m, 171 high/medium-confidence vessel labels. Report:
`ml/outputs/a0/named-outputs/results/eval_report.json`.

| Vessel length | Detected / total | Recall | 95% CI |
|---|---|---|---|
| 15-30 m | 1 / 7 | 14% | 3-51% |
| 30-60 m | 4 / 24 | 17% | 7-36% |
| 60-120 m | 21 / 30 | 70% | 52-83% |
| >= 120 m | 29 / 57 | 51% | 38-63% |
| All (53 vessels have no length) | 63 / 171 | 37% | - |

Precision 68%; 0.43 false alarms per 100 km2.

Limits: one scene, one crop chosen for label density (busier than typical open
sea), small counts per bin, no tuning on this scene. It shows that HRSID mAP@50
(0.838) does not transfer to Sentinel-1 and that sub-60 m vessels are mostly
missed. It does not measure open-sea false-alarm rates or other regions.

## 1b. First fine-tune (run A1, 2026-10-04)

`best.pt` fine-tuned on xView3 Sentinel-1 crops with HRSID replay (Azure ML,
CPU, 15 epochs, first 10 backbone layers frozen, lr 0.002). Training data:
12 crops of 4096 px from 4 xView3 training scenes (about 160 labelled vessels),
tiles with vessels plus an equal number of empty tiles, plus 150 HRSID images.
One training scene was held out for model selection. The scored scene is the same
held-out validation crop as A0 and was never used in training. Weights:
`ml/models/finetuned_xview3_a1.pt`; reports: `ml/outputs/a1/`.

| Same held-out crop (171 vessels) | A0 base | A1 fine-tuned |
|---|---|---|
| 15-30 m (n=7) | 1 | 3 |
| 30-60 m (n=24) | 4 (17%) | 14 (58%) |
| 60-120 m (n=30) | 21 (70%) | 19 (63%) |
| >= 120 m (n=57) | 29 (51%) | 35 (61%) |
| All | 63 (36.8%) | 84 (49.1%) |
| Precision | 68.5% | 70.6% |
| False alarms / 100 km2 | 0.43 | 0.52 |
| HRSID mAP@50 (150 test images) | 0.913 | 0.895 (-1.9 pts) |

Acceptance rule (decided before the run): xView3 recall must rise and HRSID mAP@50
must not fall by more than 2 points. Both held, so A1 is accepted as a candidate,
not deployed.

Limits: one scored scene and crop (chosen for label density), small bins (the
60-120 m change is within noise), little training data, the HRSID drop is close
to the 2-point limit, and the xView3 tile mAP@50 on the held-out training scene
is low (about 0.35). Treat this as evidence the approach helps, not as a final
accuracy figure. More scenes would tighten every number.

## 2. What is established about the current serving path

Everything in this table was read from code or a primary source on 2026-10-02.

| Fact | Source |
|---|---|
| The deployed detector is YOLO11n trained on HRSID; recorded mAP50 0.838, mAP50-95 0.579 on HRSID's own validation split | `backend/data/metrics.json` |
| HRSID images are 800x800 px at 0.5-3 m resolution | HRSID dataset description [D2 in the literature review] |
| Live Sentinel-1 IW GRDH has 20x22 m resolution on a 10x10 m pixel grid | ESA Sentinel-1 technical guide [R1] |
| The service fetches a +/-0.02 degree window (about 4.4 km at 8 degrees latitude) resized to 640x640, about 6.9 m per output pixel | `yolo-service/app/config.py` (`chip_half_deg`, `chip_px`) |
| That output grid is finer than Sentinel-1's native 10 m pixel, so the chip is up-sampled about 1.45x with no new information | arithmetic from the two rows above |
| The service stretches VV as `2.5 * VV` in linear power, clipped to [0,1] | `yolo-service/app/sentinel.py` evalscript |
| The offline pipeline instead converts dB `[-50, 0]` to `[0, 255]` | `ml/pipeline/tiling.py` |
| The service requests a dual-polarisation product but reads only VV | `sentinel.py` (`polarization: "DV"`, `input: ["VV"]`) |
| Area sweeps use non-overlapping chips (tile spacing 0.04 degrees equals chip width), capped at 12 tiles; the response reports `fully_covered` honestly | `backend/app/api/routes/verify.py` |
| The service confidence threshold is 0.25, while metrics and documentation state 0.45 | `config.py`, `metrics.json` |
| No detection performance has been measured on Sentinel-1 imagery | absence of any such artifact; the plan's own Stage F is the first to produce it |

## 3. Why small vessels are likely missed (hypotheses, not findings)

None of these has been measured on Sentinel-1. They are ordered by how directly the
facts above support them.

**H1: scale and resolution mismatch.** A 20 m vessel spans about two native pixels;
the training set shows ships tens of pixels long. Resolution, not pixel count, limits
what the sensor can resolve, so up-sampling the chip cannot recover it. A detector
trained at 0.5-3 m is being asked to recognise objects several times smaller than it
has seen. Pretraining and architecture research reports the same pressure: low
spatial resolution and noise make small SAR objects especially hard [M10], and the
xView3 authors describe the targets as small and sparse [D1].

**H2: three different intensity mappings.** Training imagery, the offline pipeline
and the live service each map backscatter to 8-bit differently. For illustration
only, assume open-sea VV of -20 dB, a small boat of -12 dB and a larger vessel of
-5 dB (assumptions, to be replaced by measured histograms):

| Target | Offline dB mapping `[-50,0]` | Service linear `2.5*VV` |
|---|---|---|
| Sea, -20 dB | 153 | 6 |
| Small boat, -12 dB | 194 | 40 |
| Large vessel, -5 dB | 230 | 202 |

Both mappings differ from each other, and neither is known to match the HRSID
training images (which are 8-bit products from several sensors with undocumented
conversions). A model does not transfer reliably across a change in the
brightness relationship between target and background.

**H3: speckle.** IW GRDH has an equivalent number of looks of about 4.4 [R1],
so single-pixel clutter spikes resemble point targets. A threshold low enough to
catch a 2-pixel boat will also fire on clutter unless the detector models local
statistics.

**H4: single-shot chips with border losses.** Non-overlapping chips split vessels
that straddle a tile edge.

**H5: threshold policy is unresolved.** A 0.25 service threshold and a 0.45
documented threshold mean reported precision and recall do not describe the
deployed behaviour.

## 4. What counts as "fixed": definition and limits

State the goal as a **detectability curve**: probability of detection and false
alarms per 100 km2 as a function of true vessel length. Do not claim to find all
small vessels. Below some length the sensor cannot separate a vessel from clutter
regardless of the model, and many benchmark annotations do not label very small
objects reliably. A result such as "recall for 30-60 m vessels rose from X to Y with
non-overlapping intervals, and 0-15 m vessels remain undetectable" is the honest and
publishable form.

## 5. Validation protocol (works for any fix)

1. **Data.** Use held-out xView3-SAR scenes [D1] (Sentinel-1, with vessel length
   labels). Split by whole scene. Report the high-confidence label subset and all
   labels separately. Freeze this set before tuning.
2. **Metric.** Use `ml/evaluation/detection_by_size.py`: recall per length bin with
   Wilson 95% intervals, precision, and false positives per 100 km2. Matching is by
   centre distance in metres (default 30 m, three native pixels), not box IoU, which
   is unstable for 2-3 pixel objects. `compare_reports` marks a bin change as
   `clear` only when the two intervals do not overlap.
3. **Run the same scenes, same threshold policy, before and after.** Choose any
   confidence threshold on training or validation scenes, never on the reported set.
4. **Ablate** so the effect is attributable:

   | Run | Change |
   |---|---|
   | A0 | Current service as deployed (linear `2.5*VV`, single 640 px chip, threshold 0.25) |
   | A1 | One shared preprocessing function (section 7, step 1), same model |
   | A2 | A1 plus 20-25% overlapped tiling or slicing-aided inference [M9] |
   | A3 | A2 plus classical candidate generation with the learned model as verifier |
   | A4 | A model trained on Sentinel-1-native data (xView3 tiles), same preprocessing |

5. **Gates before accepting a change.** (a) Recall in at least one small bin
   improves with non-overlapping intervals; (b) false positives per 100 km2 do not
   exceed a limit fixed before the experiment; (c) no regression on the HRSID
   validation metrics already recorded; (d) land and coastline false positives are
   reported on their own, because shoreline clutter is the usual failure of added
   sensitivity.

### Retraining guardrails (the existing model is the floor, not a starting point to discard)

These apply to any run that trains on more data. They exist so that adding data cannot
silently make the model worse.

1. **Start from the current weights** (`best.pt`, HRSID mAP@50 0.838), not from scratch,
   and never overwrite them. A new model is saved under a new name with its own
   provenance; `best.pt` stays the fallback.
2. **Mix, do not replace.** Each epoch draws from xView3 tiles and a replayed HRSID
   subset, so the model keeps what it already does well while learning 10 m
   Sentinel-1 statistics. Fine-tuning on xView3 alone is the usual way to lose HRSID
   accuracy.
3. **Split by scene, not by tile.** xView3 tiles from one scene share sea state and
   clutter; scenes (and their neighbours in time and space) go wholly into train,
   validation or test. The held-out scenes used for the A0 baseline stay held out.
4. **More data only when the data is the bottleneck.** Add scenes in steps (for
   example 5, 10, 20) and plot held-out recall against scene count. If the curve is
   flat, more data will not help and the next lever is preprocessing or
   architecture, not downloads.
5. **Accept or reject by rule, fixed before training:** the candidate replaces the
   served model only if (a) held-out xView3 recall improves in at least one size bin
   with non-overlapping 95% intervals, (b) false positives per 100 km2 stay within
   the limit, and (c) HRSID mAP@50 drops by no more than 0.02 from 0.838. Otherwise
   `best.pt` stays, and the result is reported as a negative result.
6. **Compute.** Training needs a GPU. The student subscription has no GPU quota and
   quota increases are not offered for that offer type, so training runs on a GPU
   host the user provides (Colab/Kaggle T4, or another subscription with quota); the
   Azure CPU cluster runs measurement only.

Example:

```python
from evaluation.detection_by_size import evaluate_by_size, compare_reports

before = evaluate_by_size(scenes_a0, match_radius_m=30.0, min_confidence=0.25)
after = evaluate_by_size(scenes_a2, match_radius_m=30.0, min_confidence=0.25)
for row in compare_reports(before, after):
    print(row["bin"], row["truth"], row["recall_before"], row["recall_after"], row["clear"])
```

Each scene is `{"truth": [...], "predictions": [...], "pixel_size_m": 10.0, "area_km2": ...}`
with `x_center_px`, `y_center_px`, `length_m` on truth and `confidence` on predictions.

## 6. If the fix uses OpenCV

OpenCV-based candidate search is a legitimate direction. Constant false alarm rate
(CFAR) detection is the classical baseline for exactly this problem, adaptive and
non-parametric variants target weak and small ships [C1, C2], and combinations of
classical cues with learning are reported as promising for small vessels [C3]. The
following determine whether a particular implementation is correct:

- **Name it accurately.** `cv2.adaptiveThreshold`, morphological filtering and
  connected components form a local-contrast detector. It is **not** CFAR unless it
  estimates the local clutter distribution (with guard cells around the test pixel)
  and sets the threshold from a target false-alarm probability. Without that, the
  false-alarm rate is not controlled and will vary with sea state.
- **Work in a consistent intensity domain.** Decide linear power or dB once, using
  the shared function from section 7, and apply it identically in training,
  evaluation and serving. OpenCV works on 8-bit images, so quantisation at the
  conversion step can erase faint targets; keep float32 until after detection.
- **Handle speckle deliberately.** Median or bilateral blur is a crude stand-in for
  SAR despeckling and also smears 2-pixel targets. Evaluate the choice on the size
  bins instead of assuming it helps.
- **Convert thresholds to physical units.** Minimum blob area in pixels must be
  stated in square metres and checked against the 10 m grid.
- **Mask land and structures.** Without a land mask, a more sensitive detector
  mostly adds false alarms along coasts, ports and offshore infrastructure.
- **Keep it a candidate generator.** Feed candidates to the learned model or a
  classifier for verification, and carry the source of each detection (`cfar`,
  `yolo`, `both`) into the observation record so results can be audited.
- **Test with injected targets.** Insert point targets of known intensity into real
  sea-clutter chips and measure probability of detection against signal-to-clutter
  ratio. This isolates the detector from label noise and gives a defensible
  detection curve before touching xView3.
- **Do not assert correctness from sight.** Showing extra boxes on a chip proves
  only that sensitivity increased. The section 5 gates decide whether they were
  vessels.

## 7. Improvement plan in priority order

1. **One preprocessing contract.** Create a single versioned function that turns
   Sentinel-1 VV (and VH) backscatter into model input. Import it from training,
   evaluation, the YOLO service and the backend chip fetcher, and store its version
   with every observation. This removes H2 regardless of model changes.
2. **Overlapped slicing at inference** with merged detections, using the native 10 m
   grid rather than an up-sampled one. Slicing-aided inference raised AP on aerial
   small-object benchmarks [M9]; its effect on Sentinel-1 is an experiment, not an
   assumption.
3. **Sentinel-1-native training data.** Fine-tune on xView3-SAR tiles, optionally
   after pretraining on a large mixed corpus such as SARDet-100K [D3]. Keep HRSID as
   an auxiliary source and a regression check, not the evaluation target.
4. **Architecture and loss for tiny objects.** Add a higher-resolution (stride-4)
   detection head and test the Normalized Wasserstein Distance loss that small-target
   SAR work uses [M5]. Compare a transformer detector under equal budgets [T3].
5. **Use both polarisations.** Request and use VH as well as VV; xView3 supplies
   both, and dual-polarisation data exists as a dedicated benchmark [D5].
6. **Classical candidate generation plus verifier** (section 6), evaluated as run A3.
7. **Calibrated abstention.** Report a hit as a calibrated lead with an explicit
   coverage level instead of a raw confidence, using conformal methods [U1, U4].
8. **Resolve the threshold policy.** Choose one threshold from validation data,
   store it in the model package, and make service, metrics and documentation read
   from it.

## 8. What to say publicly

Until the section 5 results exist, describe the detector as: trained and validated
on HRSID (mAP50 0.838), **not yet evaluated on live Sentinel-1 imagery**, with small
vessels expected to be a weakness because of the resolution difference, and with
hits treated as unverified leads. That statement is accurate today and is
consistent with how the interface and the Ask agent already describe the model.
