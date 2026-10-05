"""Convert extra HRSID train images (COCO) to YOLO format for the replay set.

Reads HRSID.zip + train2017.json, skips images already uploaded (--existing is a
text file of stems), and writes images/ + labels/ ready to upload to
hrsid/train/ in the xview3 blob container. Only train2017 is used, so nothing
overlaps the test2017 images used for the HRSID regression check.
"""
from __future__ import annotations

import argparse
import json
import random
import zipfile
from pathlib import Path


def coco_to_yolo(bbox: list[float], width: int, height: int) -> tuple[float, float, float, float]:
    x, y, w, h = bbox
    return ((x + w / 2) / width, (y + h / 2) / height, w / width, h / height)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--annotations", required=True)
    ap.add_argument("--existing", required=True, help="text file: one already-uploaded image stem per line")
    ap.add_argument("--out", required=True)
    ap.add_argument("--count", type=int, default=1250)
    args = ap.parse_args()

    data = json.loads(Path(args.annotations).read_text())
    have = {s.strip() for s in Path(args.existing).read_text().split() if s.strip()}
    boxes: dict[int, list] = {}
    for ann in data["annotations"]:
        boxes.setdefault(ann["image_id"], []).append(ann["bbox"])
    pool = [im for im in data["images"] if Path(im["file_name"]).stem not in have and im["id"] in boxes]
    random.Random(0).shuffle(pool)
    chosen = pool[: args.count]

    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "labels").mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.zip) as zf:
        for im in chosen:
            stem = Path(im["file_name"]).stem
            src = f"HRSID_JPG/JPEGImages/{stem}.jpg"
            (out / "images" / f"{stem}.jpg").write_bytes(zf.read(src))
            lines = [
                "0 " + " ".join(f"{v:.6f}" for v in coco_to_yolo(b, im["width"], im["height"]))
                for b in boxes[im["id"]]
            ]
            (out / "labels" / f"{stem}.txt").write_text("\n".join(lines))
    print(f"wrote {len(chosen)} images to {out}")


if __name__ == "__main__":
    main()
