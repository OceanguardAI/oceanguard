# Dataset collection and training data

This is the acquisition guide for the architecture in
[the development plan](end-to-end-development-plan.md). Collection status is
based on local files checked on September 27, 2026. A repository checkout,
example image, or unfinished archive does not count as a complete dataset.

## What data the system needs

OceanGuard has separate learning tasks. SAR image detection locates vessel
candidates in a satellite pass. Coastal video tracking follows detections over
successive frames. AIS association compares those observations against actual
messages at the same time and location. Behavior analysis uses vessel histories.
Drone imagery is an optional inspection source with a different viewpoint.
MPA polygons supply spatial context and do not train a ship detector.

The minimum research package is HRSID, SSDD, xView3, a tracking dataset,
synchronized FVessel video/AIS, and labelled historical AIS. Other datasets
support external evaluation or optional branches. Downloading every maritime
dataset is unnecessary and can introduce duplicate images and incompatible
labels. None of the new archives has been used for fine-tuning yet.

## Source register

| Dataset | Purpose | Official source and access | Collection state |
|---|---|---|---|
| HRSID | SAR detection and segmentation baseline | [Author repository](https://github.com/chaozhong2010/HRSID); [JPG archive with coastal annotations](https://drive.google.com/file/d/1NY3ovgc-woDlNoQdyqzRB3t9McOBH5Ms/view) | Repository samples/annotations present; full archive attempted, completion pending verification |
| HRSID negative images | Test land/sea clutter false positives | [Author background archive](https://drive.google.com/file/d/1U0Sj1SHoq-2VjXXUKwpXae6rBI3YjyDP/view) | Download attempted; completion pending verification |
| SSDD | Independent SAR detector evaluation | [Author repository](https://github.com/TianwenZhang0825/Official-SSDD); [official archive](https://drive.google.com/file/d/1glNJUGotrbEyk43twwB9556AdngJsynZ/view) | Documentation present; approximately 1.04 GB archive download attempted |
| xView3-SAR | Sentinel-1 full-scene detection, vessel size and fishing labels | [Challenge](https://iuu.xview.us/); [download portal](https://iuu.xview.us/download-links) | Not collected; portal access and a bounded scene selection required |
| ShipsMOT | Coastal multi-object tracking and identity recovery | [Author repository](https://github.com/jpj0916/ShipsMOT); [Baidu archive](https://pan.baidu.com/s/1gpmnm4zN2n7rI9KbWbJvDA?pwd=vgqv), code `vgqv` | Documentation/figures present; videos and tracking labels not collected |
| FVessel V1 | Synchronized video, AIS, camera calibration and association labels | [Authors](https://github.com/gy65896/FVessel); [author Hugging Face release](https://huggingface.co/datasets/gy65896/FVessel) | Author repository collected; full video/AIS archive not collected |
| SeaShips | Coastal detector diversity and hard negatives | [Author repository](https://github.com/jiaming-wang/SeaShips) | Not collected; follow author download links, distinguish public subset from full dataset |
| MVDD13 | Vessel classes and surface-camera generalization | [Author repository](https://github.com/yyuanwang1010/MVDD13); [author Drive folder](https://drive.google.com/drive/folders/1EzlGyZF9FlZRrI77XBd9Pt7RSuEwbWno) | Documentation present; full images/labels not collected |
| Singapore Maritime Dataset | Held-out shore/onboard visual evaluation | [Official page](https://sites.google.com/site/dilipprasad/home/singapore-maritime-dataset) | Not collected; retain original sequence and modality split |
| SeaDronesSee | Optional drone detection and tracking | [Official portal](https://seadronessee.cs.uni-tuebingen.de/dataset) | Not collected; select detection/tracking version and its terms |
| LaRS | Water/sky/obstacle segmentation and scene conditions | [Official page](https://lojzezust.github.io/lars-dataset/) | Not collected; name, email, affiliation and terms form required |
| UOW-Vessel | Optional optical satellite detection/segmentation | [University page](https://documents.uow.edu.au/~phung/UOW-Vessel.html) | Blocked pending signed release agreement and author-provided links |
| DTU Danish AIS anomalies | Labelled behavior evaluation and separate normal-traffic training | [Collection](https://data.dtu.dk/collections/AIS_Trajectories_from_Danish_Waters_for_Abnormal_Behavior_Detection/6287841); [labelled record](https://api.figshare.com/v2/articles/21511815); [training record](https://api.figshare.com/v2/articles/21511842) | Author utilities/docs collected; labelled file acquisition attempted; training files not collected |
| NOAA MarineCadastre AIS | Broader historical normal motion and forecasting | [Official repository](https://github.com/ocm-marinecadastre/ais-vessel-traffic); [portal](https://marinecadastre.gov/ais/) | Not collected; choose region and period before downloading |
| HOSS ReID | Optional optical/SAR identity research | [Official repository](https://github.com/Alioth2000/Hoss-ReID) links to its Zenodo dataset | Not collected; retain original identity splits and review data licence |
| Synthetic SeaDronesSee | Optional controlled viewpoint and condition experiments | [Official download portal](https://seadronessee.cs.uni-tuebingen.de/dataset) | Deferred until real-data baselines exist |
| VRX | Simulation of maritime tasks and sensor failures | [Official simulator](https://github.com/osrf/vrx) | Deferred; simulator resources are not a labelled real-world dataset |
| WDPA / Protected Planet | MPA and geofence context | [Protected Planet](https://www.protectedplanet.net/) | Existing local MPA layer must retain its own provenance and update date |

FVessel V1 contains 26 synchronized sequences and 7,625 detection images. Its
author-hosted file inventory reports `FVessel_V1.0.zip` at 40,903,480,977 bytes,
`FVessel_V2.0.zip` at 22,998,862,185 bytes, and `Clip-10.zip` at 2,559,974,618
bytes. The complete V1 package exceeds this drive's approximately 17 GB of free
space at the start of collection. The single clip can support an adapter smoke
test, but cannot establish performance across full held-out sequences.

LaRS provides separate images (966 MB), annotations (22.3 MB), and temporal
context images (13.6 GB). Start with images/annotations after completing the
provider form; the context package also needs extraction space. The UOW-Vessel
entry previously pointed to an unrelated/unverified GitHub path. The registry
now points to the author's university release page, which requires an agreement.

## Local layout and collection evidence

Verified during this collection pass:

| Local asset | Bytes | Provider MD5 | Result |
|---|---|---|---|
| DTU `data_..._600_43200_120.pkl` | 3,685,072 | `8f3d40fe17acf22f99cdacd1dc4e92d7` | Downloaded and checksum verified |
| DTU `data_..._3000_43200_600.pkl` | 776,889 | `3e9650e8f16aa5f7155b62791196f064` | Downloaded and checksum verified |
| DTU `datasetInfo_..._600_43200_120.pkl` | 14,078 | `ca2c311e139619161d7916b64fa7c008` | Downloaded and checksum verified |
| DTU `datasetInfo_..._600_99999999_0.pkl` | 15,674 | `53cd431e914394a13818b0db8fd6fd45` | Downloaded and checksum verified |
| DTU `datasetInfo_..._3000_43200_600.pkl` | 13,987 | `af84019f48472febbac40af54b15abd4` | Downloaded and checksum verified |

These files use the common prefix
`AIS_Custom_13122021_13122021_CarFisHigMilPasPleSaiTan`.
The 120-second and 600-second representations each have complete matching
metadata and verified provider checksums.
Other trajectory representations are not independent examples of new vessels.
The unlabelled DTU training article is still a separate acquisition task.

The training article offers several overlapping representations: approximately
680 MB for the June-November 120-second data, 143 MB for its 600-second data,
192 MB for a November selection, 99 MB for a December selection, and 5.37 GB for
unresampled June-November trajectories, plus metadata. Select one training
representation and retain a separate validation period. Do not use its December
selection for fitting when the labelled December 13 event is the test set.
Both checked DTU articles declare CC BY 4.0; include their attribution.

FVessel author repository inventory: 16 files excluding `.git`, with a local
SHA-256 manifest generated by the collector. This inventory contains author
documentation/utilities, not the 40.9 GB dataset archive.

Raw assets stay in the ignored directory `ml/data/external/<dataset_id>/`.
Keep original archives, extracted files and derived formats distinct:

```text
<dataset_id>/
  original/         untouched extracted dataset
  dataset-manifest.json
  derived/         adapter output, with adapter version
  splits.json      frozen sequence/scene/identity assignments
```

Existing author repository checkouts occupy the dataset root for HRSID, SSDD,
ShipsMOT and MVDD13. FVessel and DTU author repositories were also collected on
September 27. These are documentation/code sources; their presence says nothing
about the completeness of the raw dataset. Do not run downloaded training code
as part of collection.

The current machine's limited free space prevents full collection of the large
video/SAR packages. Choose an external disk or the intended Azure data storage
before bulk downloads. Record every downloaded file's expected bytes, provider
checksum when available, local SHA-256, source URL and acquisition date. Partial
files must remain `partial`, never `downloaded` or `prepared`.

## Acquisition commands

Run from the repository root. `gdown` was installed into the existing backend
virtual environment as a local download utility; this does not change runtime
dependencies. These commands fetch the archives and do not train models:

```powershell
backend\.venv\Scripts\python.exe -m gdown 'https://drive.google.com/uc?id=1NY3ovgc-woDlNoQdyqzRB3t9McOBH5Ms' -O ml/data/external/hrsid/HRSID.zip
backend\.venv\Scripts\python.exe -m gdown 'https://drive.google.com/uc?id=1U0Sj1SHoq-2VjXXUKwpXae6rBI3YjyDP' -O ml/data/external/hrsid/HRSID-negative.zip
backend\.venv\Scripts\python.exe -m gdown 'https://drive.google.com/uc?id=1glNJUGotrbEyk43twwB9556AdngJsynZ' -O ml/data/external/ssdd/SSDD.zip
```

The DTU labelled article exposes six files through the Figshare API, including
three trajectory representations and their matching metadata files. The article
declares CC BY 4.0. Choose one representation for evaluation; the alternatives
are different resamplings of the same underlying trajectories, not independent
test datasets. Preserve the attribution and inspect the author datasheet before
loading pickle files. Pickle files can execute code when deserialized.

```powershell
$datasetArticle = Invoke-RestMethod 'https://api.figshare.com/v2/articles/21511815'
$datasetArticle.files | Select-Object name,size,download_url,computed_md5
```

After a download completes, verify the archive opens and the expected sample and
label counts match. Then create the local content manifest:

```powershell
backend\.venv\Scripts\python.exe ml/collect_datasets.py --dataset hrsid
backend\.venv\Scripts\python.exe ml/collect_datasets.py --dataset ssdd
backend\.venv\Scripts\python.exe ml/collect_datasets.py --dataset fvessel
backend\.venv\Scripts\python.exe ml/collect_datasets.py --dataset dtu_ais
```

The helper inventories all files, including repository docs; a nonzero file
count alone is insufficient evidence of training readiness. Do not generate a
final manifest while a file is downloading. Dataset usage rights must be checked
separately from an accompanying code repository licence.

## Preparing data for each model

1. SAR detector: reproduce HRSID using official splits, retain hard negatives,
   and freeze SSDD as external evaluation. Add xView3 scenes with matching
   preprocessing and acquisition-level splits. Keep resolution, polarization,
   radiometric scaling and sensor metadata with each sample.
2. Coastal detector/tracker: use ShipsMOT or an approved FVessel version. Convert
   boxes without losing sequence IDs, frame times and identity labels. Never
   split adjacent video frames at random. Keep SMD as an external domain test.
3. AIS association: use genuinely synchronized FVessel observations, AIS and
   camera calibration. Unrelated historical AIS cannot create valid camera
   correspondence labels. Preserve unavailable headings and delayed messages.
4. Behavior: use DTU training data for fitting and the labelled article only for
   evaluation. Rescue and collision-related anomalies must not be labelled
   illegal fishing. NOAA/Danish historical data can extend normal traffic once
   their region/time and filtering rules are recorded.
5. Optional branches: SeaDronesSee for drone views, LaRS for scene segmentation,
   HOSS for cross-sensor re-identification, and UOW-Vessel for optical satellite
   tests. Each requires its own adapter, model evaluation and permissions.

Create deterministic group manifests with
`python -m datasets.splits` from the `ml` directory. Preserve official splits
where supplied; do not replace them with random hash splits. Reject duplicate
IDs and check near-duplicate imagery across datasets before training. Record
normalization code version, label mapping, excluded samples and reasons.

## Completion criteria

Collection is complete per dataset only when the actual imagery/video/messages
and required labels are present, file integrity is verified, usage terms are
recorded, and source inventory matches the intended release. Preparation also
requires an adapter, frozen splits and leakage checks. Model training and measured
performance are subsequent stages. Author code/docs and partial transfers do not
satisfy these criteria.
