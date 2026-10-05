# Literature review and research agenda

Prepared October 2, 2026 for the OceanGuard research plan. This is a focused
scoping review, not a systematic one: it was built from searches of arXiv/PubMed
indexes and provider documentation on that date, and every entry below was
opened and checked. Claims attributed to a paper are limited to what its
abstract or the cited page states. Numbers are the authors' own and were not
reproduced here. Items I could not verify are listed separately at the end so
they are not cited by accident.

## 1. Why the problem matters and what is already known

Global Fishing Watch (GFW) combined Sentinel-1 SAR, Sentinel-2 optical imagery,
vessel GPS and deep learning to map industrial vessels and offshore
infrastructure worldwide for 2017-2021, and concluded that 72-76% of the world's
industrial fishing vessels are not publicly tracked [P1]. That result is the
reason a SAR-versus-AIS comparison is a meaningful signal at all, and GFW's SAR
vessel-detection dataset (the feed OceanGuard reads) is derived from that work.
The xView3-SAR benchmark released nearly 1,000 analysis-ready Sentinel-1 scenes,
about 29,400 by 24,400 pixels each, with co-located bathymetry and wind rasters,
and explicitly frames the difficulty as "small and sparse" maritime objects [D1].

Takeaway for OceanGuard: the societal framing is established. The open research
space is not "can SAR find dark vessels" but how reliably, at what vessel size,
with what uncertainty, and with what provenance.

## 2. SAR ship detection

### 2.1 Datasets and what they actually are

| Dataset | Verified facts | Relevance to OceanGuard |
|---|---|---|
| HRSID [D2] | 5,604 images, 16,951 ships, 800x800 px, from Sentinel-1B, TerraSAR-X and TanDEM-X, image resolution 0.5-3 m, HH/HV/VV | Our current training set. Its pixel scale differs from live Sentinel-1 IW GRD (10 m pixels), see section 2.4 |
| xView3-SAR [D1] | ~1,000 Sentinel-1 scenes, annotated by automated plus manual analysis, bathymetry and wind rasters | The realistic target domain. The best available test of the system's actual input |
| SARDet-100K [D3] | Built from 10 existing SAR detection datasets, first COCO-scale multi-class SAR detection set; proposes a Multi-Stage with Filter Augmentation (MSFA) pretraining scheme | Large pretraining source; also documents the RGB-pretraining-versus-SAR-finetuning gap |
| iVision MRSSD [D4] | 11,590 tiles, 27,885 ships, multi-resolution | Candidate for resolution-diversity experiments |
| Dual-polarimetric ship dataset [D5] | Multi-polarisation SAR ship data; notes most public sets are single-polarisation grayscale | Relevant because live Sentinel-1 is dual-pol and the service currently uses VV only |

### 2.2 Detector architectures reported on HRSID/SSDD

Recent work reports substantial headroom on HRSID itself: SARES-DEIM, a DETR-based
detector with a sparse mixture-of-experts module, reports 76.4 mAP50:95 and 93.8
mAP50 on HRSID [M1]; RSNet reports 67.6 mAP50:95 on HRSID with 1.49 M parameters
[M2]; CASS-Det, MC-ASFF-ShipYOLO, RSTNet and SAR-ShipNet target small, dense or
multi-scale ships [M3-M6]. RSTNet specifically combines a denoising unit with the
Normalized Wasserstein Distance (NWD) loss to improve tiny-box regression [M5].

Takeaway: OceanGuard's recorded YOLO11n result (mAP50 0.838, mAP50-95 0.579 on its
HRSID validation split) sits below these reported figures on the same benchmark.
That comparison is indicative only, because splits, training budgets and
evaluation code differ, but it says a stronger in-domain detector is achievable
before any domain transfer question is addressed.

### 2.3 Pretraining and small-object techniques

- SARDet-100K found that the disparity between RGB pretraining and SAR
  fine-tuning (data domain and model structure) is a crucial challenge and
  proposed MSFA [D3]. Self-supervised masked-autoencoder pretraining on SAR gave
  a further 1.3 mAP on that benchmark [M7]. Optical-ship-detector and
  optical-SAR-matching pretraining, fused with weighted box fusion, placed sixth
  in the 2020 Gaofen SAR ship challenge [M8].
- Slicing Aided Hyper Inference (SAHI) raised AP by 5.1-6.8% for three detectors
  at inference time and by 12.7-14.5% cumulatively with slicing-aware
  fine-tuning, on the VisDrone and xView aerial benchmarks [M9]. Those are
  optical aerial benchmarks, not SAR, so the size of the effect on Sentinel-1 is
  an open measurement.
- TRANSAR combines masked pre-training on unlabelled SAR with an auxiliary
  segmentation task and a curriculum sampler to handle extreme object-to-image
  size imbalance [M10].

### 2.4 The resolution gap OceanGuard has to confront

Sentinel-1 IW GRDH products have 20x22 m spatial resolution on a 10x10 m pixel
grid [R1]. HRSID's imagery is 0.5-3 m [D2]. A 20 m fishing vessel is therefore
roughly two pixels long in live data, against tens of pixels in the training set.
Re-sampling a chip to a larger pixel count does not add information. This is the
central methodological issue for the small-vessel work and is analysed in
[small-vessel-detection-plan.md](small-vessel-detection-plan.md).

### 2.5 Classical detection (CFAR) and hybrids

Constant false alarm rate detectors remain the standard non-learning baseline
because they control the false-alarm rate against a local clutter model.
Non-parametric variants avoid assuming a clutter distribution [C1]; adaptive
CFAR using intensity and texture fusion targets small ships specifically [C2].
MCEM combines clutter-invariant learning with multiple cues for real-time
small-vessel detection and argues that both sea-clutter statistics and pure deep
learning have fundamental limits for small vessels [C3]. Hybrid designs that use
a CFAR-style detector to propose candidates and a learned model to verify them
are a plausible fit for OceanGuard but were not benchmarked by anything I found
on Sentinel-1 vessels in the 10-30 m range.

### 2.6 Dark-vessel pipelines built on these detectors

An FPGA-oriented YOLOv8 variant reports detection and classification within 2% and
3% of GPU state of the art on xView3-SAR while being far cheaper to run [P2].
FAD-SAR applies six classical detectors to xView3 and reports Avg-F1 near 0.21,
which is informative about how hard the benchmark is [P3]. A multi-task framework
for vessel detection plus gross-tonnage estimation addresses which detected
vessels are even required to carry a transponder [P4]; this matters because
"no AIS" is only suspicious for vessels that must broadcast.

## 3. Tracking and cross-sensor association

DeepSORVF and the FVessel benchmark address asynchronous AIS-video matching with
missing data and outliers [A1]. GMvA uses graph learning, an uncertainty-fusion
module and Hungarian assignment for AIS-CCTV association under incomplete,
unevenly distributed data [A2]. A homography-based image-AIS fusion pipeline
reports 74.76% association accuracy overall and 85.06% for fixed cameras [A3].
ByteTrack [T1] and BoT-SORT [T2] are the standard tracking-by-detection
baselines; RT-DETR is the real-time transformer detector the plan compares
against YOLO [T3].

Takeaway: association with missing or delayed AIS is an active topic, but the
published systems are camera-AIS. I did not find a published evaluation of
SAR-AIS association that reports abstention (`ambiguous`/`unavailable`) alongside
accuracy. That is a gap OceanGuard's four-state design is positioned to fill.

## 4. Multimodal dark-vessel systems

DarkVesselNet fuses Sentinel-1, Sentinel-2, geospatial foundation-model backbones
and AIS trajectory reasoning, but its abstract states the available evidence is
software tests (speckle filtering, band ratios, distance, gap emission and so on)
rather than detection accuracy [S1]. HARBOR derives heading and probabilistic
future positions from a single SAR image using AIS only for offline calibration
[S2]. Sea-Scan uses weak supervision from imperfect AIS labels (on distributed
acoustic sensing, not imagery) [S3]. Takeaway: end-to-end claims in this area
are often not yet backed by held-out accuracy, which makes a reproducible,
honest evaluation itself a contribution.

## 5. LLM agents for maritime decision support

- AIS-LLM combines an AIS time-series encoder with an LLM for trajectory
  prediction, anomaly detection and collision-risk assessment with explainable
  output [L1]. VTS-LLM formalises risk-prone-vessel identification as a
  knowledge-augmented Text-to-SQL task and reports that query phrasing style
  systematically changes performance [L2]. Context-enriched natural-language
  trajectory descriptions study how well LLMs describe AIS trips when given
  structured context [L3]. An equation-grounded synthetic-anomaly benchmark
  addresses the lack of labelled AIS anomalies [L4].
- General techniques that match OceanGuard's design: ReAct (interleaved reasoning
  and tool use, reported to reduce hallucination relative to reasoning alone)
  [L5] and retrieval-augmented generation, which was introduced partly to give
  generations provenance [L6].

Takeaway: maritime LLM work concentrates on AIS-only data and Text-to-SQL. I found
no work on evidence-grounded agents over SAR detections that verify their own
citations mechanically, nor adversarial testing against attacker-controlled
vessel fields (see section 7). OceanGuard's agent layer can contribute there.

## 6. Uncertainty, calibration and abstention

Conformal prediction gives distribution-free coverage guarantees and has been
extended to object detection: Sequential Conformal Risk Control for the two-stage
detection setting [U1], two-step conformal prediction that propagates class
uncertainty into box intervals [U2], scaled conformal prediction with
class-wise calibration under distribution shift [U3], and selective conformal
risk control, which couples abstention with calibrated sets [U4]. None of these
was evaluated on SAR vessels in what I found. OceanGuard already treats
abstention as first-class in association (`unavailable`/`ambiguous`); extending
that to detections gives a principled answer to "how sure is this hit".

## 7. Data provenance and provider drift

GFW's own release notes record that the AIS dataset v20231026 was deprecated
early, that comparing its outputs with v3 "is currently not possible", that AIS
data between 26 January and 10 April 2024 contained an error and analyses should
be repeated, and that new pipeline versions v3 (2024) and v4 (2026) were released
[G1]. On 2 October 2026 GFW announced that pipeline v5 becomes the `latest` alias
on 21 October, with v4 remaining available under `:v4.0` but no longer updated
[G2]. Takeaway: upstream data versions change under users, sometimes with
errors, and a system that records which version produced each result and can
quantify drift between versions is doing something most dashboards do not.

## 8. Gap analysis: what OceanGuard can contribute

These are gaps relative to what this review found. "I did not find" is not proof
that no work exists.

| ID | Gap | Why OceanGuard is positioned for it |
|---|---|---|
| G1 | Version-aware dark-vessel pipeline with a quantified drift study between provider data versions | v5 lands during this project; the repo already stores dataset identity per record and now records the resolved version |
| G2 | Detection performance reported by physical vessel length on Sentinel-1, with detectability curves and honest negative results for HRSID-to-Sentinel-1 transfer | The domain gap is already observed; the size-binned evaluator exists in `ml/evaluation/detection_by_size.py` |
| G3 | SAR-AIS association evaluated with abstention under controlled outages | Four-state association policy is implemented (`backend/app/services/association.py`) |
| G4 | Evidence-grounded agents with machine-checkable citations, abstention, and prompt-injection robustness over maritime data | Deterministic evidence layer exists; agent plan in [agent-architecture-plan.md](agent-architecture-plan.md) |
| G5 | A reproducible failure benchmark combining G1-G4 | Dataset registry, group-safe splits and replay tooling are in place |

## 9. Research questions

Each question names the experiment, the data and the way it can fail, so a
negative result is still reportable.

- **RQ1 (provider drift).** How much does the GFW SAR-presence activity layer
  change between pipeline v4 and v5 over identical windows, and does it change
  which cells fall inside or near protected areas?
  Experiment: `python -m app.tools.compare_gfw_versions` over several fixed
  windows and regions; report cell Jaccard, detection ratio, count correlation,
  top-cell stability and per-context totals. Fails informatively if v5 is
  indistinguishable from v4, which is itself a finding.
- **RQ2 (small-vessel detectability).** What is the probability of detection of
  the current model, and of a Sentinel-1-native retrained model, as a function of
  true vessel length on held-out xView3 scenes?
  Experiment: size-binned recall with Wilson intervals and false alarms per
  100 km2; ablate preprocessing, overlapped tiling, CFAR candidates and
  native-resolution training. Risk: xView3 labels are partly automated, so
  report results separately for the high-confidence label subset.
- **RQ3 (abstention).** Does conformal or ensemble-based abstention on detections
  reduce false alerts at fixed recall compared with a single confidence
  threshold? Risk: calibration sets are small for rare vessel sizes.
- **RQ4 (association under outages).** How do accuracy and abstention behave for
  SAR-AIS association as AIS sampling is degraded (delay, loss, bursts)?
  Experiment: synthetic outages on top of natural gaps; precision versus
  coverage curves. Synthetic outages supplement, not replace, natural gaps.
- **RQ5 (agent faithfulness).** What fraction of identifiers and numbers in agent
  outputs can be traced to tool results, how does it change across models and
  prompts, and does a mechanical citation verifier plus abstention reduce
  unsupported claims, including under injected instructions in vessel fields?

## 10. Threats to validity and ethics

- Label noise: xView3 combines automated and manual labels [D1]; report on the
  high-confidence subset and as sensitivity analysis.
- Leakage: split by whole scene or acquisition, never by tile; HRSID tiles from one
  parent scene overlap by design [D2].
- Metric choice: IoU is unstable for 2-3 pixel objects; use centre-distance
  matching in metres and cross-check with official scorers before publication.
- Provider dependence: results are conditioned on a GFW dataset version; always
  state it.
- Dual use and harm: a SAR hit without AIS is a lead, not evidence of an offence.
  The system must keep identity, behaviour and priority separate, avoid
  accusatory language, and keep a human in the loop. Dataset licences must be
  checked before redistributing derived data.

## 11. References (verified on 2026-10-02)

Context and data
- [P1] Paolo, F. S., Kroodsma, D. et al. "Satellite mapping reveals extensive industrial activity at sea." Nature, 2024. https://www.nature.com/articles/s41586-023-06825-8 (existence and headline finding confirmed via Global Fishing Watch release notes and press coverage; the PMC copy is PMC10764273.)
- [D1] xView3-SAR: Detecting Dark Fishing Activity Using Synthetic Aperture Radar Imagery. arXiv:2206.00897.
- [D2] Wei, S., Su, H., Ming, J., Wang, C., Yan, M., Kumar, D., Shi, J., Zhang, X. HRSID: a high-resolution SAR images dataset for ship detection and instance segmentation. IEEE Access, 2020. Dataset: https://github.com/chaozhong2010/HRSID. Specifications confirmed from dataset descriptions; confirm the DOI before formal citation.
- [D3] SARDet-100K: Towards Open-Source Benchmark and ToolKit for Large-Scale SAR Object Detection. arXiv:2403.06534.
- [D4] iVision MRSSD: a comprehensive multi-resolution SAR ship detection dataset. Data in Brief, 2023. PMC10471922, doi:10.1016/j.dib.2023.109505.
- [D5] A Dual-Polarimetric SAR Ship Detection Dataset and a Memory-Augmented Autoencoder-Based Detection Method. Sensors, 2021. PMC8709314, doi:10.3390/s21248478.

Detection methods
- [M1] SARES-DEIM: Sparse Mixture-of-Experts Meets DETR for Robust SAR Ship Detection. arXiv:2604.04127.
- [M2] RSNet: A Light Framework for The Detection of SAR Ship Detection. arXiv:2410.23073.
- [M3] Enhancing, Refining, and Fusing: Towards Robust Multi-Scale and Dense Ship Detection (CASS-Det). arXiv:2501.06053.
- [M4] MC-ASFF-ShipYOLO: Improved Algorithm for Small-Target and Multi-Scale Ship Detection for SAR Images. Sensors, 2025. PMC12074152, doi:10.3390/s25092940.
- [M5] RSTNet: Enhancing Small-Target Recognition in Noisy SAR Imagery via Robust Feature Learning and Distribution-Aware Regression. arXiv:2602.23820.
- [M6] SAR-ShipNet. arXiv:2203.15480.
- [M7] Enhancing SAR Object Detection with Self-Supervised Pre-training on Masked Auto-Encoders. arXiv:2501.11249.
- [M8] Boosting ship detection in SAR images with complementary pretraining techniques. arXiv:2103.08251.
- [M9] Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection (SAHI). arXiv:2202.06934.
- [M10] SAR Object Detection with Self-Supervised Pretraining and Curriculum-Aware Sampling (TRANSAR). arXiv:2504.13310.

Classical and hybrid detection
- [C1] Wilcoxon Nonparametric CFAR Scheme for Ship Detection in SAR Image. arXiv:2402.18579.
- [C2] Adaptive CFAR Method for SAR Ship Detection Using Intensity and Texture Feature Fusion Attention Contrast Mechanism. Sensors, 2022. PMC9659258, doi:10.3390/s22218116.
- [C3] MCEM: Multi-Cue Fusion with Clutter Invariant Learning for Real-Time SAR Ship Detection. Sensors, 2025. PMC12473879, doi:10.3390/s25185736.

Dark-vessel pipelines
- [P2] Efficient SAR Vessel Detection for FPGA-Based On-Satellite Sensing. arXiv:2507.04842.
- [P3] FAD-SAR: A Novel Fishing Activity Detection System via SAR Images Based on Deep Learning. arXiv:2404.18245.
- [P4] SAR Vessel Detection and Gross Tonnage Estimation from Heterogeneous Datasets for Dark Vessel Identification. arXiv:2607.18051.

Association and tracking
- [A1] Asynchronous Trajectory Matching-Based Multimodal Maritime Data Fusion for Vessel Traffic Surveillance in Inland Waterways (DeepSORVF, FVessel). arXiv:2302.11283.
- [A2] Graph Learning-Driven Multi-Vessel Association: Fusing Multimodal Data for Maritime Intelligence (GMvA). arXiv:2504.09197.
- [A3] Image and AIS Data Fusion Technique for Maritime Computer Vision Applications. arXiv:2312.05270.
- [T1] ByteTrack: Multi-Object Tracking by Associating Every Detection Box. arXiv:2110.06864.
- [T2] BoT-SORT: Robust Associations Multi-Pedestrian Tracking. arXiv:2206.14651.
- [T3] DETRs Beat YOLOs on Real-time Object Detection (RT-DETR). arXiv:2304.08069.

Multimodal systems
- [S1] DarkVesselNet: Multi-Modal Remote Sensing and Trajectory Reasoning for Dark Vessel Detection. arXiv:2606.00445.
- [S2] HARBOR: Heading Analysis and Reconstruction from Behavioral Observation and Radar. arXiv:2606.14006.
- [S3] Sea-Scan: ML-based Dark Vessel Detection and Localisation via Weakly Supervised DAS Monitoring. arXiv:2606.21326.

LLM agents
- [L1] AIS-LLM: A Unified Framework for Maritime Trajectory Prediction, Anomaly Detection, and Collision Risk Assessment with Explainable Forecasting. arXiv:2508.07668.
- [L2] VTS-LLM: Domain-Adaptive LLM Agent for Enhancing Awareness in Vessel Traffic Services through Natural Language. arXiv:2505.00989.
- [L3] Context-Enriched Natural Language Descriptions of Vessel Trajectories. arXiv:2603.12287.
- [L4] Redefining Maritime Anomaly Detection via Equation-Grounded Synthetic Anomalies. arXiv:2606.29721.
- [L5] ReAct: Synergizing Reasoning and Acting in Language Models. arXiv:2210.03629.
- [L6] Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. arXiv:2005.11401.

Uncertainty
- [U1] Conformal Object Detection by Sequential Risk Control. arXiv:2505.24038.
- [U2] Adaptive Bounding Box Uncertainties via Two-Step Conformal Prediction. arXiv:2403.07263.
- [U3] Probabilistic Object Detection with Conformal Prediction. arXiv:2605.07549.
- [U4] Selective Conformal Risk Control. arXiv:2512.12844.

Standards and provider documentation
- [R1] ESA Sentinel-1 SAR Technical Guide, IW GRD resolutions: https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-1-sar/products-algorithms/level-1-algorithms/ground-range-detected/iw/ (IW GRDH: 20x22 m resolution, 10x10 m pixel spacing).
- [G1] Global Fishing Watch API release notes: https://globalfishingwatch.org/our-apis/documentation/docs/release-notes (read 2026-10-02).
- [G2] Global Fishing Watch email "Data Pipeline v5 early access", 2 October 2026 (received by the project owner; summarised in [gfw-v5-migration.md](gfw-v5-migration.md)).

### Not verified: check before citing

These are referred to elsewhere in the repository but were not opened during this
review: the SSDD paper (Zhang et al., Remote Sensing, 2021), the LS-SSDD-v1.0
paper, the SAR-Ship-Dataset paper, the FVessel journal version beyond [A1], the
GMvA IEEE publication record (the arXiv version [A2] was verified), ShipsMOT,
SeaDronesSee, LaRS and the DTU abnormal-trajectory dataset papers. The HRSID
journal DOI should also be confirmed.
