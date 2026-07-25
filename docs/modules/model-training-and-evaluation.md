# Model Training and Evaluation

## 1. What this document explains

This document is the focused reference for the trained vessel-detection model in OceanGuard:

- what model was used
- what data it was trained on
- what validation data was used
- which evaluation metrics were selected
- why those metrics are the correct ones for this kind of problem
- why the tracked run used 50 epochs
- how the recorded ML metrics relate to the live product

This is the document to read when you want to understand the model as an engineering decision, not just as a file called `best.pt`.

## 2. Source-of-truth files

The current tracked values in this repo come from these files:

- `backend/data/metrics.json`
- `docs/data-dictionary.md`
- `docs/responsible-ai.md`
- `yolo-service/README.md`
- `yolo-service/app/config.py`

When numbers disagree across prose and code, prefer `backend/data/metrics.json` for the published model metrics because the backend serves that file directly through `GET /model-metrics`.

## 3. Model summary

The deployed verification model is:

- `YOLO11n`

Its role is:

- detect vessel-like objects in SAR image chips
- provide an independent radar-based verification path
- complement the AIS-based Global Fishing Watch ingest path

This means the model is not the only intelligence layer in OceanGuard.

It is one specialized component inside a broader system:

- GFW provides primary live SAR detections plus server-side AIS cross-matching
- the YOLO model provides an independent second look on fresh SAR chips
- the backend combines detection context, AIS state, and MPA proximity into operational risk events

## 4. Data related to the model

### Full source dataset description

The main training dataset described in the repo is:

- `HRSID` — High-Resolution SAR Images Dataset

Recorded dataset facts:

- `5,604` SAR images
- `16,951` ship instance annotations
- COCO-format labels
- multi-sensor SAR imagery including TerraSAR-X, Sentinel-1, and GF-3

### Tracked split used for the published metrics

The published metrics file records this experiment label:

- `HRSID (2857 train / 715 val)`

So the tracked checkpoint behind the backend metrics is associated with:

- `2,857` training images
- `715` validation images

Important note:

The repo currently contains both:

- the full HRSID dataset description
- the smaller tracked split name used for the published checkpoint

So if you need to speak precisely:

- use `5,604 images / 16,951 annotations` for the full dataset description
- use `2,857 train / 715 val` for the specific recorded experiment that produced the published metrics

### Additional validation scene

The repo also records a real-scene validation check on:

- `xView3` scene `590dd08f71056cacv`

Tracked details:

- location: Gulf of Guinea
- band used: `VH_dB.tif`
- scene dimensions: `28,676 x 24,522`
- resolution: `10 m`
- tiles produced: `1,174`
- resulting detections on that scene: `122`

This is important because the project does not stop at dataset-level validation only.

It also records how the model behaves on a real georeferenced SAR scene.

## 5. Why YOLO11n was selected

The repo does not include a long explicit written model-comparison memo, but the implementation strongly suggests why `YOLO11n` fits this project:

- it is a standard object-detection architecture, so it matches the task shape well
- it is lightweight enough to run in an on-demand Cloud Run inference service
- it can return bounding boxes plus confidence scores, which the UI and backend can use directly
- it supports practical fine-tuning on a moderate SAR dataset

This matters because OceanGuard needs a model that is not only accurate enough, but also deployable in a real product workflow.

The system needs:

- acceptable detection quality
- fast enough inference
- manageable runtime cost
- practical deployment in a separate container service

`YOLO11n` is therefore a product-oriented choice, not only a research-oriented one.

## 6. Why these evaluation methods were selected

### The short answer

The project uses:

- `mAP@50`
- `mAP@50-95`
- `precision`
- `recall`
- confidence threshold tracking
- epoch-by-epoch `map50` and `loss`
- a real-scene detection count on xView3

These are the right choices because this is an **object-detection** problem, not a plain image-classification problem.

### Why plain accuracy is not enough

Plain classification accuracy answers a simpler question:

- did the model assign the right class label to the whole image?

That is not the core problem here.

OceanGuard needs the model to answer:

- is there a vessel?
- where is it?
- how many are there?
- how confident is the detector?

For that reason, plain accuracy would hide important failure modes:

- a vessel was found but boxed badly
- one of multiple vessels was missed
- too many false detections were produced
- detections are sensitive to the confidence threshold

That is why object-detection metrics were chosen instead.

### Why mAP@50

`mAP@50` is the easiest high-level detection metric to communicate.

It measures whether predicted boxes overlap ground-truth boxes at an IoU threshold of `0.50`.

Why it is useful here:

- it gives a standard benchmark number for object detection
- it is easy to compare across training checkpoints
- it captures both localization and classification together
- it is widely understood by reviewers and engineers

In this repo, `mAP@50` is the headline metric and the published value is:

- `0.838`

### Why mAP@50-95

`mAP@50-95` is stricter.

Instead of testing only one overlap threshold, it averages performance across multiple IoU thresholds from `0.50` to `0.95`.

Why that matters:

- it rewards tighter localization
- it is harder to game with loose boxes
- it better reflects box quality, not just rough object presence

That is why it appears beside `mAP@50` in the published metrics:

- `mAP@50 = 0.838`
- `mAP@50-95 = 0.579`

This pairing is useful because:

- `mAP@50` tells you the detector is finding ships well
- `mAP@50-95` tells you localization is meaningfully harder than simple coarse detection

### Why precision

`Precision` answers:

- when the model predicts a vessel, how often is it correct?

Why this matters in OceanGuard:

- too many false positives create review fatigue
- patrol or analyst workflows can become noisy
- evidence cards look less credible if detections are unreliable

Published precision:

- `0.830`

### Why recall

`Recall` answers:

- of the real vessels present, how many did the model successfully detect?

This is especially important for OceanGuard because a missed vessel can be operationally worse than a false alarm.

The system is designed as a conservation decision-support tool, so it leans toward surfacing suspicious activity rather than silently missing it.

Published recall:

- `0.818`

### Why both precision and recall are needed

Precision alone can look good if the model predicts very conservatively.

Recall alone can look good if the model predicts too aggressively.

Using both prevents misleading conclusions:

- high precision + low recall means the model is cautious but misses too much
- high recall + low precision means the model floods operators with false alarms

OceanGuard needs balance, so both metrics are tracked.

### Why confidence threshold is part of evaluation

The repo records:

- `confidence_threshold = 0.45`

This matters because detection metrics change depending on the threshold.

The threshold is part of the operational definition of what counts as a detection.

The repo's own documentation explains the product posture clearly:

- the threshold is tuned toward recall
- missing a relevant vessel is considered worse than showing some extra false positives

That choice matches the system's use case:

- human review
- patrol prioritization
- conservation-risk surfacing

not autonomous enforcement.

### Why epoch-by-epoch history is stored

The metrics file keeps a simple history of:

- `epoch`
- `map50`
- `loss`

This is useful because a single final number does not show how training behaved.

The training history lets you see:

- whether the model improved steadily
- whether performance plateaued
- whether loss kept dropping
- whether the final checkpoint looks reasonable instead of arbitrary

Tracked history:

| Epoch | mAP@50 | Loss |
|---|---:|---:|
| 1 | 0.61 | 1.80 |
| 10 | 0.72 | 1.20 |
| 20 | 0.78 | 0.90 |
| 30 | 0.81 | 0.70 |
| 40 | 0.83 | 0.60 |
| 50 | 0.838 | 0.55 |

This history shows a healthy pattern:

- `mAP@50` rises consistently
- loss falls consistently
- gains become smaller toward the end

That is the kind of curve you want from a fine-tuning run.

## 7. Why 50 epochs was used

The repo records:

- `epochs = 50`

There is not a separate explicit design note saying "50 was chosen because of X", so the most honest explanation comes from the recorded training history.

### What the history suggests

By epoch:

- `1`, the model is already learning but far from stable
- `10`, it has improved significantly
- `20` and `30`, it is still making meaningful gains
- `40` and `50`, it is still improving, but more slowly

So the tracked run suggests:

- training long enough to move beyond early fast gains
- stopping at a point where improvement has not fully collapsed, but has clearly slowed

That makes `50` a practical fine-tuning length:

- long enough to converge meaningfully
- short enough to keep training cost and time manageable
- supported by the final plateau-like curve in the metrics file

### Why not use a much smaller epoch count

Stopping earlier, such as at `10` or `20`, would have left measurable performance on the table:

- `10`: `mAP@50 = 0.72`
- `20`: `mAP@50 = 0.78`
- `50`: `mAP@50 = 0.838`

So the later epochs were still valuable.

### Why not claim that more epochs are always better

The recorded curve is flattening by the end.

That means:

- additional epochs might still help a little
- but the return on extra training time is shrinking

The repo therefore supports a practical conclusion:

- `50` was a reasonable engineering stop point for this tracked checkpoint

not a magical universally optimal number.

## 8. Other recorded training-related details

The repo documentation also records these details for the tracked run:

- image size: `640`
- hardware: `T4 GPU`
- approximate training time: `~1.69 hours`

These matter because they explain the operational shape of the run:

- `640` is a common compromise between detail retention and training cost
- a `T4 GPU` is realistic for accessible cloud fine-tuning
- `~1.69 hours` suggests this was an efficient fine-tuning workflow rather than a giant research-scale training job

## 9. Why the xView3 scene matters

The HRSID metrics are important, but the project also records a validation scene on `xView3`.

That is valuable because it adds a second kind of evidence:

- dataset-level benchmark metrics from HRSID
- georeferenced scene-level behavior from xView3

Why this is a good choice:

- OceanGuard is a geospatial product, not only a benchmark project
- the backend eventually needs real-world coordinates, not just abstract labels
- a scene-level check helps reveal how the model behaves in a more operational context

The repo records:

- `122` detections on the xView3 validation scene

This is not the same thing as a full benchmark score, but it is still useful operational validation.

## 10. How runtime inference is aligned with training

The deployed YOLO service deliberately fetches a compact SAR chip sized to match the training regime reasonably well.

Recorded runtime geometry:

- around `4.4 km` across
- `640 px`
- roughly `7 m/px`

Why this was done:

- a model usually behaves better when inference-time inputs resemble training-time scale
- ships that appear at a similar spatial scale are easier for the detector to interpret reliably

This is an important engineering detail because model quality is not only about the checkpoint.

It is also about whether the runtime input distribution resembles what the model learned.

## 11. How model evaluation differs from product evaluation

The model metrics above evaluate the detector itself.

But OceanGuard as a product uses more than the detector.

Operational decisions also depend on:

- AIS match or non-match
- protected-area proximity
- repeated detections
- human review status
- live backend ingestion behavior

So a good answer about the system should distinguish between:

### Model evaluation

- `mAP@50`
- `mAP@50-95`
- `precision`
- `recall`
- confidence threshold behavior
- training history

### Product-level decision support

- GFW SAR ingest quality
- AIS cross-reference quality
- MPA spatial lookup quality
- risk-score policy
- human review workflow

This distinction is important because someone can ask, "How accurate is the system?"

The honest answer is:

- the detector has published object-detection metrics
- the full product is a multi-signal decision-support workflow, not a single classifier

## 12. Current tracked values

These are the current repo-tracked model values:

| Field | Value |
|---|---|
| Model | `YOLO11n` |
| Dataset label in metrics file | `HRSID (2857 train / 715 val)` |
| Epochs | `50` |
| mAP@50 | `0.838` |
| mAP@50-95 | `0.579` |
| Precision | `0.830` |
| Recall | `0.818` |
| Confidence threshold | `0.45` |
| Validation scene | `xView3 590dd08f71056cacv` |
| Detections on validation scene | `122` |
| Full dataset description | `5,604 images`, `16,951 annotations` |
| Recorded split used | `2,857 train / 715 val` |
| Training image size | `640` |
| Runtime verification chip | `640 px`, about `4.4 km` across |
| Runtime scale | about `7 m/px` |
| Documented hardware | `T4 GPU` |
| Documented training time | about `1.69 hours` |

## 13. Limits and honest caveats

There are a few things the repo does **not** currently provide in a deeply formal training note:

- a full experiment log with optimizer and learning-rate schedule
- a model-comparison study across multiple architectures
- a complete written explanation of how the tracked `2857 / 715` split was produced from the full HRSID corpus

So the correct way to talk about this project is:

- confidently use the tracked published metrics
- confidently explain why those metrics are appropriate
- be honest about which choices are directly documented versus inferred from the run history and deployment shape

That honesty makes the explanation stronger, not weaker.

## 14. Practical summary

If you need the shortest technically correct explanation:

OceanGuard fine-tunes a `YOLO11n` SAR ship detector on `HRSID` and tracks standard object-detection metrics rather than plain accuracy because the task requires both finding vessels and localizing them. The published checkpoint is recorded as `50` epochs on `HRSID (2857 train / 715 val)` and achieved `mAP@50 0.838`, `mAP@50-95 0.579`, `precision 0.830`, and `recall 0.818`, with a runtime confidence threshold of `0.45` chosen to favor recall in a human-review conservation workflow. The repo also records a real-scene `xView3` validation pass with `122` detections, and the live verification service fetches `640 px` SAR chips at roughly training-like scale so runtime inference stays aligned with how the model was fine-tuned.
