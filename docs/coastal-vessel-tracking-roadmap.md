# Coastal Vessel Tracking Research Roadmap

## 1. The plan in one sentence

OceanGuard will detect vessels, keep a reliable track of each vessel over time,
compare those tracks with AIS broadcasts and protected-area rules, and show a
human reviewer what is known, what is uncertain, and what needs investigation.

A drone is not the main detector and is not required for the first version. A
drone is an optional sensor that can be sent to inspect a small area after the
main system finds something important. Public drone datasets can also help us
test whether the vision model works from a moving aerial camera, even when we do
not own or operate a real drone.

## 2. The easiest mental model

The upgraded product has seven separate jobs:

1. **Detect:** find vessel-shaped objects in an image or video frame.
2. **Track:** connect repeated detections so the system knows which observations
   probably belong to the same vessel.
3. **Associate:** compare a visual or radar track with time-aligned AIS tracks.
4. **Understand:** calculate motion, dwell time, route deviation, zone entry,
   encounters, and other explainable behavior indicators.
5. **Assess uncertainty:** state when identity or behavior cannot be determined
   reliably instead of forcing an answer.
6. **Alert:** create a reviewable alert when evidence and operational context
   justify attention.
7. **Review:** let a human inspect the source evidence and decide what to do.

These jobs must not be treated as the same thing. Detecting a vessel does not
identify it. Failing to find an AIS match does not prove that a transponder was
deliberately disabled. Finding a vessel near a Marine Protected Area (MPA) does
not prove illegal fishing.

## 3. Where each sensor fits

| Source | What it is good at | What it cannot prove alone | Planned role |
|---|---|---|---|
| Coastal CCTV or port camera | Frequent observations, shape, direction, local movement | Vessel identity without another source; activity outside the camera view | Primary source for continuous coastal tracking |
| AIS | Reported identity, position, speed, course, heading, and navigation status | Non-broadcasting vessels; truthful identity in every case | Identity and motion evidence aligned by time |
| Satellite SAR | Wide-area vessel-like returns through cloud and darkness | Continuous movement, exact identity, intent, or guaranteed detection of every small vessel | Periodic offshore/coastal observation and supporting evidence |
| Optical satellite imagery | Easier visual interpretation and vessel appearance | Cloud-free, frequent, continuous coverage | Optional recognition and cross-modal research |
| Drone RGB or thermal camera | Close, targeted, flexible observation | Wide-area continuous coverage; legal permission; automatic identity | Optional follow-up after an alert and a research test domain |
| MPA, port, route, and weather layers | Operational and geographic context | Whether an observed vessel is committing an offence | Context for explainable behavior indicators |

### Why drones appear in the research plan

Drone datasets are useful because a drone camera introduces difficult but
valuable conditions: small vessels, changing altitude, camera motion, glare,
waves, partial occlusion, and unusual viewing angles. Training and testing on
these examples can make the vision and tracking pipeline more robust.

This does **not** mean that OceanGuard currently controls a drone. There are two
different uses:

- **Dataset use now:** evaluate detection and tracking on public datasets such
  as SeaDronesSee. This is software research and needs no physical drone.
- **Operational use later:** an authorized operator sends a drone to a selected
  coordinate and its stream becomes another observation source. This requires
  hardware, connectivity, aviation permission, georeferencing, and a partner.

The first research version will work with recorded public camera, AIS, SAR, and
drone data. A real drone integration is a later pilot, not a dependency.

## 4. The target end-to-end flow

```text
Coastal camera/video -----> vessel detections -----> visual tracks -----+
                                                                       |
AIS history/stream --------> cleaned AIS tracks -----------------------+--> association
                                                                       |    with uncertainty
Satellite SAR -------------> dated SAR observations ------------------+
                                                                            |
MPA/port/routes/weather ----> operational context --------------------------+
                                                                            |
                                                                            v
                         behavior and data-quality indicators
                                                                            |
                                                                            v
                          reviewable alert + evidence timeline
                                                                            |
                                        optional authorized drone follow-up
                                                                            |
                                                                            v
                              human analyst decision and feedback
```

### Example

1. A coastal camera detects a small vessel at 10:02.
2. The tracker links it to detections at 10:03 and 10:04 and creates one track,
   not three vessels.
3. AIS contains two possible vessels near that camera view. The association
   model compares time, motion, projected camera position, and appearance.
4. If one candidate is strongly supported, the track is marked `matched`. If
   evidence is weak or two candidates are similar, it is marked `ambiguous`.
5. If AIS is unavailable, the track is marked `unavailable`, not `dark`.
6. The behavior engine notices that the vessel has remained near a restricted
   zone for 25 minutes. This creates a loitering candidate with its supporting
   measurements; it does not declare illegal activity.
7. An analyst reviews the video, AIS timeline, map context, and uncertainty.
8. If a real drone integration exists and local rules allow it, the analyst may
   request a closer look. Otherwise the workflow ends with the available data.

## 5. What must change in the current product

### A. Stop losing and misrepresenting observations

The current GFW path converts aggregated grid reports into records that look
like exact vessel observations. It also reduces map density by retaining one
high-risk record in a large cell and sampling records by risk level. That can
make real observations disappear.

The upgraded design will:

- store all valid source observations with stable source identifiers;
- keep source time and ingestion time as separate values;
- represent a GFW aggregate as an activity cell, not an individual vessel;
- use clustering, viewport filtering, and pagination only when displaying data;
- never invent a current timestamp or model confidence for a missing value;
- retain the last known good dataset when a provider refresh fails.

### B. Separate observations from tracks

An observation is one measurement from one sensor at one time. A track is a
time-ordered hypothesis connecting multiple observations. A predicted point is
not a measured point and must have a different status and visual style.

Each track should use these states:

- `observed`: supported by a current sensor measurement;
- `predicted`: estimated between measurements, with uncertainty;
- `lost`: the system expected another observation but did not receive one;
- `unobservable`: no suitable sensor coverage was available.

### C. Treat AIS matching as an uncertain association

AIS association must compare observations from the same time window. It should
use position, speed, course, heading, camera calibration, track history, and
uncertainty. The result should be one of:

- `matched`: one identity has sufficient evidence;
- `unmatched`: adequate AIS coverage existed but no candidate passed the rule;
- `ambiguous`: several candidates remain plausible;
- `unavailable`: AIS data or coverage was insufficient.

Only `unmatched` under adequate coverage is a possible non-cooperative-vessel
signal. Even then, it is not proof that AIS was intentionally switched off.

### D. Make alerts explainable

Detection confidence, identity confidence, sensor quality, behavior score, and
operational priority are different values. They must not be merged into one
number that appears more certain than the evidence.

Initial behavior indicators should include:

- reported navigation status inconsistent with observed motion;
- unusual dwell or loitering outside known anchorage areas;
- entry into a configured zone;
- route deviation from a learned local pattern;
- close or prolonged vessel encounters;
- stale, missing, or contradictory sensor data.

Every alert must show the measurements and rule that created it. Gemini may
explain the evidence in plain language, but it must not establish identity,
change the measurements, or declare wrongdoing.

## 6. Proposed data model

The research system needs four persistent concepts:

| Record | Meaning | Example fields |
|---|---|---|
| `Observation` | One sensor measurement | source, source ID, source time, ingestion time, location, geometry uncertainty, sensor quality, evidence reference |
| `Track` | A vessel hypothesis over time | track ID, state, positions, prediction uncertainty, first/last observed times |
| `Association` | Evidence linking a track to a reported identity | track ID, AIS candidate, confidence, status, method, model version |
| `Alert` | A reviewable operational condition | type, severity, evidence, uncertainty, created time, model/rule version, review state |

PostgreSQL with PostGIS should hold structured spatial and temporal records.
Immutable image/video evidence and model outputs should be stored in object
storage with hashes and provenance. The present `RiskEvent` API can remain as a
compatibility view while the frontend moves to versioned observation, track,
alert, and coverage APIs.

## 7. Model and experiment plan

### Detection

Reproduce the existing YOLO11 result first. Then compare YOLO11 and a small
RT-DETRv2 model using the same splits, image resolution, compute budget, and
evaluation rules. Test hard-negative mining, overlapping SAR tiles, shoreline
clutter, day/night conditions, and small-vessel performance.

### Tracking

Establish ByteTrack and BoT-SORT baselines. The main research method will add
observation age, sensor availability, motion uncertainty, calibration error,
and an option to reject an unsafe identity assignment. The goal is to recover
tracks after gaps without silently connecting different vessels.

### Association

Compare geometric/time-aligned matching with DeepSORVF-style asynchronous
matching and reproducible parts of GMvA. The research contribution is not
simply "AIS plus computer vision"; that already exists. The contribution is a
reproducible failure benchmark and an association method that remains
calibrated when data are delayed, missing, or contradictory.

### Behavior analysis

Start with explainable rules and probabilistic baselines. Add learned trajectory
forecasting only after the track data are trustworthy. Train on normal traffic
separately from annotated abnormal examples, and do not mix artificial anomaly
results with results from real labelled incidents.

## 8. Dataset order

1. **FVessel:** first synchronized video/AIS association benchmark.
2. **ShipsMOT:** maritime multi-object tracking and appearance variation.
3. **Singapore Maritime Dataset:** external coastal visual evaluation.
4. **NOAA and Danish AIS:** historical route, motion, and forecasting data.
5. **DTU abnormal trajectories:** limited but human-labelled anomaly evaluation.
6. **xView3:** primary realistic Sentinel-1 SAR benchmark.
7. **HRSID and SSDD:** supporting SAR detector training and comparison.
8. **SeaDronesSee:** moving-camera, aerial, and small-object robustness.
9. **LaRS and MaCVi thermal:** water clutter, obstacles, and low-light testing.
10. **HOSS ReID and ShipRSImageNet:** optional identity and recognition studies.

For every dataset, record its version, source, licence, allowed use, sensor,
geography, time range, label quality, known duplicates, and official split.
Split by complete video, capture session, location, vessel identity, or parent
satellite scene. Random neighbouring frames or tiles must not be divided across
training and test sets because that would leak nearly identical data.

## 9. How success will be measured

Different tasks need different metrics:

| Task | Main measures |
|---|---|
| Detection | mAP50-95, precision, recall, small-vessel recall, false alarms per image or area |
| Tracking | HOTA, IDF1, identity switches, fragmentation, recovery time after a gap |
| AIS association | precision, recall, assignment coverage, false association rate, calibration error |
| Forecasting | ADE and FDE at declared time horizons |
| Behavior alerts | event precision/recall and false alerts per vessel-hour |
| Product | p50/p95 latency, provider freshness, processing cost, review completion time |

The first hypotheses to test are 5-10 additional HOTA points, 20-40% fewer
identity switches, and 20-30% fewer false alerts relative to reproduced
baselines. These are experiment targets, not promised results.

## 10. Six-month implementation sequence

### Weeks 1-2: make current evidence trustworthy

- diagnose hosted HTTP 500 failures from logs and direct provider checks;
- stop dropping GFW records in storage;
- represent aggregate cells honestly;
- preserve source timestamps and stable identifiers;
- change empty AIS from "confirmed dark" to `unavailable`;
- make verification idempotent and stop automatic score inflation;
- expose source freshness and provider failure states.

### Weeks 3-6: build reproducible research inputs

- create the dataset and licence register;
- download only the selected public datasets;
- create leakage-safe, versioned splits;
- build synchronized replay for video, AIS, detections, and ground truth;
- reproduce detector and tracker baselines with stored configurations and raw
  predictions.

### Weeks 7-10: improve detection and tracking

- compare YOLO11 and RT-DETRv2 fairly;
- compare ByteTrack and BoT-SORT;
- mine recurring false positives and missed small vessels;
- test resolution, overlap, sensor-specific preprocessing, and appearance
  features;
- select models from validation data and test once on frozen held-out data.

### Weeks 11-16: implement the main research contribution

- add availability-aware, time-aligned association;
- model uncertainty and allow abstention;
- recover tracks after realistic observation gaps;
- test AIS delay, packet loss, burst outage, video occlusion, clock skew, and
  calibration error;
- perform component ablations and equal-budget baseline comparisons.

### Weeks 17-20: add behavior and analyst workflows

- add contextual behavior and data-quality alerts;
- add track history, coverage, source freshness, and uncertainty to the UI;
- persist cases, reviews, evidence, and audit records;
- implement human feedback without silently changing historical model outputs.

### Weeks 21-24: freeze and evaluate

- freeze models and rules before final tests;
- run cross-dataset and failure-condition evaluation;
- report confidence intervals, limitations, latency, and cost;
- package reproducible code, manifests, results, and a research paper draft;
- define a future live coastal/drone pilot without claiming it has already been
  validated.

## 11. Release rules

The upgraded system is acceptable only when:

- empty AIS produces `unavailable`, never "confirmed dark";
- the same verification request cannot repeatedly increase risk;
- delayed data retain their original source times;
- provider failures do not erase the last valid observations;
- tracks and reviews survive restarts and multiple backend instances;
- predicted locations are visibly different from measured locations;
- every alert links to source evidence, model/rule version, and uncertainty;
- deployment is blocked when the frozen evaluation suite fails.

## 12. What the final product will and will not be

At the end of this roadmap, OceanGuard should be a rigorously evaluated regional
coastal vessel-tracking research prototype with auditable evidence and honest
uncertainty. It can support an analyst by finding, following, and prioritizing
vessels that deserve review.

It will not automatically prove illegal fishing, diagnose mechanical failure,
identify every vessel, or provide continuous global coverage. It will not be a
certified navigation or enforcement system. Those claims require operational
partners, calibrated sensors, legal processes, and extensive real-world trials.

## 13. Research references

- FVessel and DeepSORVF: <https://github.com/gy65896/FVessel>
- GMvA multimodal vessel association: <https://doi.org/10.1109/TITS.2026.3655007>
- MaCVi 2026 benchmark overview: <https://arxiv.org/abs/2604.13244>
- ShipsMOT: <https://github.com/jpj0916/ShipsMOT>
- SeaDronesSee: <https://seadronessee.cs.uni-tuebingen.de/dataset>
- LaRS: <https://lojzezust.github.io/lars-dataset>
- DTU AIS abnormal-behavior data: <https://doi.org/10.11583/DTU.c.6287841.v1>
- xView3: <https://arxiv.org/abs/2206.00897>
- HRSID: <https://github.com/chaozhong2010/HRSID>
- HOSS optical-SAR vessel re-identification: <https://github.com/Alioth2000/Hoss-ReID>
- ByteTrack: <https://github.com/FoundationVision/ByteTrack>
- RT-DETR: <https://github.com/lyuwenyu/RT-DETR>
- Global Fishing Watch 4Wings report semantics:
  <https://globalfishingwatch.org/our-apis/documentation/docs/v3/4wings/report>
