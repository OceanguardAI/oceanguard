# OceanGuard Dataset Collection

This directory is the controlled entry point for external training and
evaluation data. Raw datasets are intentionally not committed to Git. They
belong in ml/data/external/, which is ignored by the repository.

The registry is a catalog, not evidence that files have already been downloaded.
Each dataset must pass four gates before training:

1. Confirm the upstream source and usage terms.
2. Download outside the Git repository's tracked files.
3. Record the local file count and SHA-256 manifest.
4. Convert labels into a versioned adapter without changing the untouched
   source copy.

## Initial collection order

1. HRSID and SSDD: reproduce the current SAR baseline and test cross-dataset generalization.
2. xView3-SAR: evaluate Sentinel-1 fishing/non-fishing labels. It requires an account and challenge terms.
3. ShipsMOT: establish the first video tracking and identity-switch baseline.
4. SeaShips and MVDD13: add coastal appearance variation and hard negatives.
5. LaRS: add water, sky, obstacle, and degraded-scene context.
6. UOW-Vessel: keep as a separate optical-satellite transfer test.

Do not concatenate all datasets into one training folder. Their sensors,
viewpoints, labels, resolutions, and licensing terms differ. First reproduce
the HRSID baseline, then evaluate SSDD and xView3 without training on test data.

## Status meanings

- catalogued: source and intended use are recorded; raw files are not present.
- downloaded: raw files exist locally and a manifest has been written.
- prepared: an adapter produced a derived training format from a verified source.
- blocked: access, license, or integrity validation needs user action.

The current repository state is catalogued only. No fine-tuning result should
be reported from these datasets until files, splits, and manifests are present.

## Local collection performed on September 26, 2026

- HRSID: public repository checkout with sample image/annotation assets and a
  local SHA-256 manifest. The full Google Drive archive is not present.
- SSDD: public repository checkout with license and documentation only; the
  full image archive is not present.
- MVDD13: public repository checkout with license and documentation only; the
  full image archive is not present.
- ShipsMOT: public repository checkout with documentation and figures only;
  the video archive remains at the upstream download location.
- xView3-SAR: not downloaded because the official challenge download requires
  an account and acceptance of its terms.
