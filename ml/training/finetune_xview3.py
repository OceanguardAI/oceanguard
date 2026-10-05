"""Fine-tune the HRSID-trained YOLO model on xView3 crops, with HRSID replay.

Runs inside an Azure ML command job (CPU is fine for this small dataset). The
new weights are only worth keeping if they beat the baseline on a held-out
xView3 scene AND do not lose accuracy on HRSID; this script scores both so the
decision is mechanical.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
from pathlib import Path

TILE = 640
PIXEL_M = 10.0
UNKNOWN_LENGTH_BOX_PX = 12.0
MIN_BOX_PX = 6.0
MAX_BOX_PX = 64.0


def box_side_px(length_m: float | None) -> float:
    """Square box side in pixels for a vessel of the given length."""
    if length_m is None:
        return UNKNOWN_LENGTH_BOX_PX
    return min(MAX_BOX_PX, max(MIN_BOX_PX, 1.3 * length_m / PIXEL_M))


def tile_labels(
    truth: list[dict], row_off: int, col_off: int, tile: int = TILE
) -> list[tuple[float, float, float, float]]:
    """YOLO (cx, cy, w, h), normalised, for truth vessels whose centre is in the tile."""
    out = []
    for item in truth:
        cx = float(item["x_center_px"]) - col_off
        cy = float(item["y_center_px"]) - row_off
        if not (0 <= cx < tile and 0 <= cy < tile):
            continue
        side = box_side_px(item.get("length_m"))
        x0, x1 = max(0.0, cx - side / 2), min(float(tile), cx + side / 2)
        y0, y1 = max(0.0, cy - side / 2), min(float(tile), cy + side / 2)
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        out.append(
            ((x0 + x1) / 2 / tile, (y0 + y1) / 2 / tile, (x1 - x0) / tile, (y1 - y0) / tile)
        )
    return out


def _write_split(
    crops_dir: Path,
    labels_csv: Path,
    crop_ids: list[str],
    out_dir: Path,
    neg_ratio: float,
    rng: random.Random,
) -> int:
    from evaluation.detection_by_size import load_xview3_truth
    from pipeline.tiling import tile_sar

    img_dir, lab_dir = out_dir / "images", out_dir / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lab_dir.mkdir(parents=True, exist_ok=True)
    positives = negatives = 0
    for cid in crop_ids:
        tif = crops_dir / cid / "VH_dB.tif"
        truth = load_xview3_truth(str(labels_csv), cid)
        tmp = out_dir / f"_tiles_{cid}"
        tiles = tile_sar(str(tif), str(tmp))
        pos, neg = [], []
        for row_off, col_off, path in tiles:
            boxes = tile_labels(truth, row_off, col_off)
            (pos if boxes else neg).append((path, boxes))
        rng.shuffle(neg)
        keep = pos + neg[: int(len(pos) * neg_ratio)]
        for path, boxes in keep:
            name = f"{cid}_{Path(path).stem}"
            shutil.copy(path, img_dir / f"{name}.png")
            (lab_dir / f"{name}.txt").write_text(
                "\n".join(f"0 {a:.6f} {b:.6f} {c:.6f} {d:.6f}" for a, b, c, d in boxes)
            )
        positives += len(pos)
        negatives += min(len(neg), int(len(pos) * neg_ratio))
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"  {out_dir.name}: {positives} positive + {negatives} negative tiles")
    return positives


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-crops", required=True)
    ap.add_argument("--train-labels", required=True)
    ap.add_argument("--hrsid", required=True, help="folder with train/ and test/ (images/ labels/)")
    ap.add_argument("--eval-scenes", required=True)
    ap.add_argument("--eval-labels", required=True)
    ap.add_argument("--base-model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--val-scene", default="e98ca5aba8849b06t")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--hrsid-replay", type=int, default=150)
    ap.add_argument("--neg-ratio", type=float, default=1.0)
    ap.add_argument("--lr0", type=float, default=0.002)
    ap.add_argument("--freeze", type=int, default=10)
    args = ap.parse_args()

    from ultralytics import YOLO

    from evaluation.detection_by_size import _run_xview3

    rng = random.Random(0)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path("/tmp/ds")
    shutil.rmtree(work, ignore_errors=True)

    crops = Path(args.train_crops)
    crop_ids = sorted(p.name for p in crops.iterdir() if (p / "VH_dB.tif").exists())
    val_ids = [c for c in crop_ids if c.startswith(args.val_scene)]
    train_ids = [c for c in crop_ids if c not in val_ids]
    print(f"train crops {len(train_ids)}, val crops {len(val_ids)}")
    _write_split(crops, Path(args.train_labels), train_ids, work / "train", args.neg_ratio, rng)
    _write_split(crops, Path(args.train_labels), val_ids, work / "val", args.neg_ratio, rng)

    hr_train = sorted((Path(args.hrsid) / "train" / "images").glob("*"))
    rng.shuffle(hr_train)
    for img in hr_train[: args.hrsid_replay]:
        lab = Path(args.hrsid) / "train" / "labels" / f"{img.stem}.txt"
        shutil.copy(img, work / "train" / "images" / f"hr_{img.name}")
        shutil.copy(lab, work / "train" / "labels" / f"hr_{img.stem}.txt")

    (work / "xview3.yaml").write_text(
        f"path: {work}\ntrain: train/images\nval: val/images\nnames:\n  0: vessel\n"
    )
    hr_test = Path(args.hrsid) / "test"
    (work / "hrsid.yaml").write_text(
        f"path: {hr_test}\ntrain: images\nval: images\nnames:\n  0: vessel\n"
    )

    def hrsid_map(weights: str) -> float:
        res = YOLO(weights).val(data=str(work / "hrsid.yaml"), imgsz=640, device="cpu", verbose=False)
        return float(res.box.map50)

    summary: dict = {"hrsid_map50_base": hrsid_map(args.base_model)}
    print("base HRSID mAP50", summary["hrsid_map50_base"])

    model = YOLO(args.base_model)
    model.train(
        data=str(work / "xview3.yaml"), epochs=args.epochs, imgsz=TILE, batch=8, device="cpu",
        workers=2, freeze=args.freeze, lr0=args.lr0, patience=6, project=str(out / "runs"), name="ft",
        exist_ok=True, seed=0, plots=False,
    )
    best = out / "runs" / "ft" / "weights" / "best.pt"
    shutil.copy(best, out / "finetuned.pt")
    summary["hrsid_map50_finetuned"] = hrsid_map(str(best))

    for tag, weights in (("base", args.base_model), ("finetuned", str(best))):
        report = _run_xview3(
            args.eval_scenes, weights, 0.25, str(out / f"xview3_eval_{tag}.json"),
            labels_csv=args.eval_labels,
        )
        summary[f"xview3_recall_{tag}"] = report.overall_recall
        summary[f"xview3_precision_{tag}"] = report.precision
    summary["accept"] = (
        summary["xview3_recall_finetuned"] > summary["xview3_recall_base"]
        and summary["hrsid_map50_finetuned"] >= summary["hrsid_map50_base"] - 0.02
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
