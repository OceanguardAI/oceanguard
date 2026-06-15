"""Run YOLO inference across SAR tiles."""
from __future__ import annotations

import json
import os
from pathlib import Path

import torch
from ultralytics import YOLO


def _parse_offsets(tile_path: str) -> tuple[int, int]:
    """Extract row/column offsets from tile filenames."""
    name = Path(tile_path).stem
    parts = name.split("_")
    row_off = int(parts[1][1:])
    col_off = int(parts[2][1:])
    return row_off, col_off


def detect_tiles(
    tile_dir: str,
    model_path: str,
    conf_threshold: float = 0.45,
    chunk_size: int = 25,
    checkpoint_path: str | None = None,
) -> list[dict]:
    """Return YOLO detections, optionally resuming from a checkpoint."""
    torch.set_num_threads(2)
    model = YOLO(model_path)

    all_tiles = sorted(str(path) for path in Path(tile_dir).glob("tile_r*.png"))

    processed_tiles: set[str] = set()
    detections: list[dict] = []
    if checkpoint_path and os.path.exists(checkpoint_path):
        with open(checkpoint_path, encoding="utf-8") as f:
            checkpoint = json.load(f)
        detections = checkpoint.get("detections", [])
        processed_tiles = set(checkpoint.get("processed_tiles", []))
        print(
            f"Resuming: {len(processed_tiles)} tiles already processed, "
            f"{len(detections)} detections so far"
        )

    remaining_tiles = [tile for tile in all_tiles if tile not in processed_tiles]
    print(f"Tiles to process: {len(remaining_tiles)}")

    for chunk_start in range(0, len(remaining_tiles), chunk_size):
        batch_paths = remaining_tiles[chunk_start : chunk_start + chunk_size]
        results = model.predict(
            source=batch_paths,
            conf=conf_threshold,
            verbose=False,
            device="cpu",
        )

        for tile_path, result in zip(batch_paths, results):
            row_off, col_off = _parse_offsets(tile_path)

            if result.boxes is None or len(result.boxes) == 0:
                processed_tiles.add(tile_path)
                continue

            for box in result.boxes:
                xyxy = box.xyxy[0].tolist()
                x_center = (xyxy[0] + xyxy[2]) / 2
                y_center = (xyxy[1] + xyxy[3]) / 2

                detections.append(
                    {
                        "tile_path": tile_path,
                        "row_off": row_off,
                        "col_off": col_off,
                        "x_center_px": round(x_center, 2),
                        "y_center_px": round(y_center, 2),
                        "width_px": round(xyxy[2] - xyxy[0], 2),
                        "height_px": round(xyxy[3] - xyxy[1], 2),
                        "confidence": round(float(box.conf[0]), 4),
                        "class_id": int(box.cls[0]),
                    }
                )
            processed_tiles.add(tile_path)

        if checkpoint_path:
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "detections": detections,
                        "processed_tiles": list(processed_tiles),
                    },
                    f,
                )

        print(
            f"  Chunk {chunk_start // chunk_size + 1}: "
            f"{len(batch_paths)} tiles, {len(detections)} detections total"
        )

    print(f"Detection complete: {len(detections)} detections")
    return detections


if __name__ == "__main__":
    detections = detect_tiles(
        "tiles/",
        "models/best.pt",
        checkpoint_path="outputs/detect_checkpoint.json",
    )
    print(f"Total detections: {len(detections)}")
