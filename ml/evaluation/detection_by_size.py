"""Vessel-size-binned detection metrics for small-vessel experiments.

Aggregate mAP hides exactly the failure OceanGuard cares about: a model can score
well overall while missing most vessels shorter than a few Sentinel-1 pixels.
This evaluator reports recall per physical vessel length, plus false alarms per
area, so a "small-ship fix" can be shown to help (or not) on the same scenes.

Matching is by centre distance in metres, not box IoU. A 2-3 pixel vessel moves
IoU from 0.9 to 0.1 with a one-pixel shift, so IoU is dominated by labelling
noise at this scale. Final publication numbers should still be cross-checked
against the benchmark's official scorer (e.g. the xView3 metric).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import hypot, inf, sqrt
from typing import Any, Iterable, Mapping, Sequence

# Length-bin edges in metres. Sentinel-1 IW GRD pixels are 10 m, so the first
# bins hold vessels at or below roughly one to three pixels.
DEFAULT_BIN_EDGES_M: tuple[float, ...] = (0.0, 15.0, 30.0, 60.0, 120.0, inf)


@dataclass(frozen=True)
class BinResult:
    label: str
    truth: int
    detected: int
    recall: float | None
    recall_ci95: tuple[float, float] | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SizeBinnedReport:
    match_radius_m: float
    min_confidence: float
    bins: list[BinResult]
    overall_truth: int
    overall_detected: int
    overall_recall: float | None
    predictions: int
    false_positives: int
    precision: float | None
    false_positives_per_100km2: float | None

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["bins"] = [item.as_dict() for item in self.bins]
        return data


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% Wilson score interval; stays informative for small bin counts."""
    if total <= 0:
        return None
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _bin_label(low: float, high: float) -> str:
    return f">={low:g} m" if high == inf else f"{low:g}-{high:g} m"


def _bin_index(length_m: float | None, edges: Sequence[float]) -> int | None:
    if length_m is None:
        return None
    for index in range(len(edges) - 1):
        if edges[index] <= length_m < edges[index + 1]:
            return index
    return None


def _match(
    truth: list[Mapping[str, Any]],
    predictions: list[Mapping[str, Any]],
    pixel_size_m: float,
    radius_m: float,
) -> tuple[set[int], set[int]]:
    """Greedy one-to-one nearest matching; returns matched truth/prediction indices."""
    candidates: list[tuple[float, int, int]] = []
    for ti, expected in enumerate(truth):
        for pi, actual in enumerate(predictions):
            distance_m = pixel_size_m * hypot(
                float(expected["x_center_px"]) - float(actual["x_center_px"]),
                float(expected["y_center_px"]) - float(actual["y_center_px"]),
            )
            if distance_m <= radius_m:
                candidates.append((distance_m, ti, pi))
    matched_truth: set[int] = set()
    matched_pred: set[int] = set()
    for _, ti, pi in sorted(candidates):
        if ti in matched_truth or pi in matched_pred:
            continue
        matched_truth.add(ti)
        matched_pred.add(pi)
    return matched_truth, matched_pred


def evaluate_by_size(
    scenes: Iterable[Mapping[str, Any]],
    *,
    bin_edges_m: Sequence[float] = DEFAULT_BIN_EDGES_M,
    match_radius_m: float = 30.0,
    min_confidence: float = 0.0,
) -> SizeBinnedReport:
    """Score predictions against truth, binned by true vessel length.

    Each scene is a mapping with ``truth`` (``x_center_px``, ``y_center_px`` and
    ``length_m``), ``predictions`` (``x_center_px``, ``y_center_px``,
    ``confidence``), ``pixel_size_m`` (default 10.0) and optional ``area_km2``
    used for the false-alarm rate. Truth without ``length_m`` is counted overall
    but not assigned to a size bin. Report all scenes of a held-out split
    together; do not tune ``min_confidence`` on the scenes being reported.
    """
    edges = list(bin_edges_m)
    if len(edges) < 2 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise ValueError("bin_edges_m must be strictly increasing with at least two edges")
    if match_radius_m <= 0:
        raise ValueError("match_radius_m must be positive")

    truth_per_bin = [0] * (len(edges) - 1)
    hit_per_bin = [0] * (len(edges) - 1)
    truth_total = detected_total = prediction_total = false_positive_total = 0
    area_total = 0.0
    area_known = True

    for scene in scenes:
        pixel_size = float(scene.get("pixel_size_m", 10.0))
        if pixel_size <= 0:
            raise ValueError("pixel_size_m must be positive")
        truth = list(scene.get("truth", []))
        predictions = [
            p for p in scene.get("predictions", [])
            if float(p.get("confidence", 1.0)) >= min_confidence
        ]
        matched_truth, matched_pred = _match(truth, predictions, pixel_size, match_radius_m)

        for index, item in enumerate(truth):
            truth_total += 1
            detected = index in matched_truth
            detected_total += detected
            raw_length = item.get("length_m")
            bin_index = _bin_index(None if raw_length is None else float(raw_length), edges)
            if bin_index is not None:
                truth_per_bin[bin_index] += 1
                hit_per_bin[bin_index] += detected

        prediction_total += len(predictions)
        false_positive_total += len(predictions) - len(matched_pred)
        if scene.get("area_km2") is None:
            area_known = False
        else:
            area_total += float(scene["area_km2"])

    bins = [
        BinResult(
            label=_bin_label(edges[i], edges[i + 1]),
            truth=truth_per_bin[i],
            detected=hit_per_bin[i],
            recall=(hit_per_bin[i] / truth_per_bin[i]) if truth_per_bin[i] else None,
            recall_ci95=wilson_interval(hit_per_bin[i], truth_per_bin[i]),
        )
        for i in range(len(edges) - 1)
    ]
    return SizeBinnedReport(
        match_radius_m=match_radius_m,
        min_confidence=min_confidence,
        bins=bins,
        overall_truth=truth_total,
        overall_detected=detected_total,
        overall_recall=(detected_total / truth_total) if truth_total else None,
        predictions=prediction_total,
        false_positives=false_positive_total,
        precision=((prediction_total - false_positive_total) / prediction_total)
        if prediction_total else None,
        false_positives_per_100km2=(false_positive_total / area_total * 100)
        if area_known and area_total > 0 else None,
    )


XVIEW3_PIXEL_SIZE_M = 10.0
_TRUE_VALUES = {"true", "1", "yes"}


def load_xview3_truth(
    labels_csv: str,
    scene_id: str,
    allowed_confidence: Sequence[str] = ("HIGH", "MEDIUM"),
) -> list[dict[str, Any]]:
    """Vessel ground truth for one scene from an xView3 label CSV.

    Keeps rows with ``is_vessel`` true and a label confidence in
    ``allowed_confidence``. ``length_m`` is None when the label has no length
    (those vessels count overall but fall in no size bin).
    """
    import csv

    allowed = {c.upper() for c in allowed_confidence}
    truth: list[dict[str, Any]] = []
    with open(labels_csv, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("scene_id") != scene_id:
                continue
            if str(row.get("is_vessel", "")).strip().lower() not in _TRUE_VALUES:
                continue
            if allowed and str(row.get("confidence", "")).strip().upper() not in allowed:
                continue
            raw_length = (row.get("vessel_length_m") or "").strip()
            try:
                length = float(raw_length) if raw_length else None
            except ValueError:
                length = None
            if length is not None and length != length:  # NaN
                length = None
            truth.append(
                {
                    "x_center_px": float(row["detect_scene_column"]),
                    "y_center_px": float(row["detect_scene_row"]),
                    "length_m": length,
                }
            )
    return truth


def _find_scene_image(scene_dir: Any) -> Any:
    for name in ("VH_dB.tif", "VH_dB.tiff", "vh_dB.tif"):
        candidate = scene_dir / name
        if candidate.exists():
            return candidate
    return None


def _run_xview3(
    scenes_dir: str,
    model_path: str,
    conf: float,
    out: str,
    labels_csv: str | None = None,
    match_radius_m: float = 30.0,
) -> SizeBinnedReport:
    """Run the current model over xView3 scenes and write a size-binned report.

    Expected layout (the xView3 download format)::

        <scenes_dir>/<scene_id>/VH_dB.tif
        <scenes_dir>/labels.csv   (or pass labels_csv)

    Each scene is tiled with the production tiler (640 px, dB[-50,0]), run
    through the production detector on CPU, and scored against the labels.
    ``area_km2`` counts only tiles that held valid data.
    """
    import json
    import tempfile
    from pathlib import Path

    from pipeline.detect import detect_tiles
    from pipeline.tiling import tile_sar

    root = Path(scenes_dir)
    labels_path = Path(labels_csv) if labels_csv else root / "labels.csv"
    if not labels_path.exists():
        raise FileNotFoundError(f"labels CSV not found: {labels_path}")

    scene_dicts: list[dict[str, Any]] = []
    for scene_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        tif = _find_scene_image(scene_dir)
        if tif is None:
            print(f"  Skipping {scene_dir.name}: no VH_dB.tif")
            continue

        with tempfile.TemporaryDirectory() as tile_dir:
            tiles = tile_sar(str(tif), tile_dir)
            detections = detect_tiles(tile_dir, model_path, conf_threshold=conf)

        predictions = [
            {
                "x_center_px": d["col_off"] + d["x_center_px"],
                "y_center_px": d["row_off"] + d["y_center_px"],
                "confidence": d["confidence"],
            }
            for d in detections
        ]
        truth = load_xview3_truth(str(labels_path), scene_dir.name)
        area_km2 = len(tiles) * 640 * 640 * XVIEW3_PIXEL_SIZE_M**2 / 1e6
        scene_dicts.append(
            {
                "scene_id": scene_dir.name,
                "pixel_size_m": XVIEW3_PIXEL_SIZE_M,
                "area_km2": area_km2,
                "truth": truth,
                "predictions": predictions,
            }
        )
        print(f"  {scene_dir.name}: {len(truth)} truth vessels, {len(predictions)} predictions")

    if not scene_dicts:
        raise RuntimeError(f"no scenes with VH_dB.tif found under {root}")

    report = evaluate_by_size(scene_dicts, min_confidence=conf, match_radius_m=match_radius_m)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report.as_dict(), handle, indent=2)
    print(f"\nReport written to {out}")
    return report


def compare_reports(before: SizeBinnedReport, after: SizeBinnedReport) -> list[dict[str, Any]]:
    """Per-bin recall change between two runs scored with the same bins.

    A change is only marked ``clear`` when the 95% intervals do not overlap, so
    a handful of vessels cannot be reported as an improvement.
    """
    if [b.label for b in before.bins] != [b.label for b in after.bins]:
        raise ValueError("reports must use identical size bins")
    rows: list[dict[str, Any]] = []
    for old, new in zip(before.bins, after.bins):
        delta = None if old.recall is None or new.recall is None else new.recall - old.recall
        clear = (
            old.recall_ci95 is not None and new.recall_ci95 is not None
            and (new.recall_ci95[0] > old.recall_ci95[1] or new.recall_ci95[1] < old.recall_ci95[0])
        )
        rows.append({
            "bin": old.label,
            "truth": old.truth,
            "recall_before": old.recall,
            "recall_after": new.recall,
            "delta": delta,
            "clear": clear,
        })
    return rows


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Size-binned recall evaluation on xView3 Sentinel-1 scenes."
    )
    parser.add_argument(
        "--scenes-dir", required=True,
        help="Directory of xView3 scenes. Each sub-dir must contain VH.tif and labels.csv."
    )
    parser.add_argument(
        "--model", required=True,
        help="Path to YOLO model weights (e.g. ml/models/best.pt)."
    )
    parser.add_argument(
        "--out", required=True,
        help="Output path for the JSON report (e.g. outputs/eval_report.json)."
    )
    parser.add_argument(
        "--conf", type=float, default=0.25,
        help="Confidence threshold for predictions (default: 0.25)."
    )
    parser.add_argument(
        "--match-radius-m", type=float, default=30.0,
        help="Max centre distance in metres to count as a match (default: 30.0)."
    )
    parser.add_argument(
        "--labels", default=None,
        help="xView3 label CSV (default: <scenes-dir>/labels.csv)."
    )
    args = parser.parse_args()

    report = _run_xview3(
        scenes_dir=args.scenes_dir,
        model_path=args.model,
        conf=args.conf,
        out=args.out,
        labels_csv=args.labels,
        match_radius_m=args.match_radius_m,
    )

    # Print summary table to stdout for the Azure ML job log
    print("\n=== Size-binned recall ===")
    for b in report.bins:
        if b.truth == 0:
            continue
        ci = f"  95% CI [{b.recall_ci95[0]:.2f}, {b.recall_ci95[1]:.2f}]" if b.recall_ci95 else ""
        print(f"  {b.label:<20} recall={b.recall:.3f}  n={b.truth}{ci}")
    print(f"  {'Overall':<20} recall={report.overall_recall:.3f}  n={report.overall_truth}")
    if report.precision is not None:
        print(f"  Precision     = {report.precision:.3f}")
    if report.false_positives_per_100km2 is not None:
        print(f"  FP/100 km²    = {report.false_positives_per_100km2:.2f}")
    print(f"\nReport saved to: {args.out}")
