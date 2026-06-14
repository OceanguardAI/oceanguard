"""Run YOLO11n inference over SAR tiles. Chunked + resumable."""
from __future__ import annotations
import json
import os
import torch
from pathlib import Path
from ultralytics import YOLO


def _parse_offsets(tile_path: str) -> tuple[int, int]:
    """Extract row_off, col_off from filename tile_rROWW_cCOLL.png."""
    name = Path(tile_path).stem          # e.g. tile_r0640_c1280
    parts = name.split("_")              # ['tile', 'r0640', 'c1280']
    row_off = int(parts[1][1:])          # strip 'r'
    col_off = int(parts[2][1:])          # strip 'c'
    return row_off, col_off


def detect_tiles(
    tile_dir: str,
    model_path: str,
    conf_threshold: float = 0.45,
    chunk_size: int = 25,
    checkpoint_path: str | None = None,
) -> list[dict]:
    """Return list of detection dicts. Resumable via checkpoint_path."""
    torch.set_num_threads(2)  # prevent memory overload on CPU

    model = YOLO(model_path)

    # Collect all tile paths
    all_tiles = sorted(
        str(p) for p in Path(tile_dir).glob("tile_r*.png")
    )

    # Resume: load existing checkpoint
    done: set[str] = set()
    detections: list[dict] = []
    if checkpoint_path and os.path.exists(checkpoint_path):
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        detections = checkpoint.get("detections", [])
        done = set(checkpoint.get("processed_tiles", []))
        print(f"Resuming: {len(done)} tiles already processed, "
              f"{len(detections)} detections so far")

    remaining = [t for t in all_tiles if t not in done]
    print(f"Tiles to process: {len(remaining)}")

    # Process in chunks
    for chunk_start in range(0, len(remaining), chunk_size):
        batch_paths = remaining[chunk_start: chunk_start + chunk_size]

        # Run inference — predict returns one Results object per image
        results = model.predict(
            source=batch_paths,
            conf=conf_threshold,
            verbose=False,
            device="cpu",
        )

        # CRITICAL: zip paths with results — never rely on r.path
        for tile_path, r in zip(batch_paths, results):
            row_off, col_off = _parse_offsets(tile_path)

            if r.boxes is None or len(r.boxes) == 0:
                done.add(tile_path)
                continue

            for box in r.boxes:
                xyxy = box.xyxy[0].tolist()    # [x1, y1, x2, y2]
                x_center = (xyxy[0] + xyxy[2]) / 2
                y_center = (xyxy[1] + xyxy[3]) / 2

                detections.append({
                    "tile_path":    tile_path,
                    "row_off":      row_off,
                    "col_off":      col_off,
                    "x_center_px":  round(x_center, 2),
                    "y_center_px":  round(y_center, 2),
                    "width_px":     round(xyxy[2] - xyxy[0], 2),
                    "height_px":    round(xyxy[3] - xyxy[1], 2),
                    "confidence":   round(float(box.conf[0]), 4),
                    "class_id":     int(box.cls[0]),
                })
            done.add(tile_path)

        # Save checkpoint after every chunk
        if checkpoint_path:
            with open(checkpoint_path, "w") as f:
                json.dump(
                    {"detections": detections,
                     "processed_tiles": list(done)},
                    f
                )
        print(f"  Chunk {chunk_start//chunk_size + 1}: "
              f"{len(batch_paths)} tiles, "
              f"{len(detections)} detections total")

    print(f"Detection complete: {len(detections)} detections")
    return detections


if __name__ == "__main__":
    dets = detect_tiles("tiles/", "models/best.pt",
                        checkpoint_path="outputs/detect_checkpoint.json")
    print(f"Total detections: {len(dets)}")
