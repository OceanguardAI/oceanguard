"""Run the full SAR inference pipeline from a raw GeoTIFF."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.detect import detect_tiles
from pipeline.georeference import georeference_detections
from pipeline.tiling import tile_sar


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run tiling, detection, and georeferencing on a SAR GeoTIFF.")
    parser.add_argument("--tif-path", type=Path, required=True, help="Path to the source SAR GeoTIFF.")
    parser.add_argument("--model-path", type=Path, required=True, help="Path to the YOLO weights file.")
    parser.add_argument(
        "--tiles-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "tiles",
        help="Directory for generated tile PNGs.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs" / "detections_scene1_georef.json",
        help="Path for the georeferenced detections JSON.",
    )
    parser.add_argument(
        "--checkpoint-path",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs" / "detect_checkpoint.json",
        help="Optional resumable checkpoint file for YOLO detection.",
    )
    parser.add_argument("--tile-size", type=int, default=640, help="Tile width/height in pixels.")
    parser.add_argument("--conf-threshold", type=float, default=0.45, help="YOLO confidence threshold.")
    parser.add_argument("--chunk-size", type=int, default=25, help="Number of tiles per YOLO batch.")
    return parser.parse_args()


def run_inference_pipeline(
    tif_path: Path,
    model_path: Path,
    tiles_dir: Path,
    output_path: Path,
    checkpoint_path: Path | None,
    tile_size: int = 640,
    conf_threshold: float = 0.45,
    chunk_size: int = 25,
) -> dict:
    """Run tiling, detection, and georeferencing; return a summary dict."""
    tif_path = tif_path.resolve()
    model_path = model_path.resolve()
    tiles_dir = tiles_dir.resolve()
    output_path = output_path.resolve()
    checkpoint_path = checkpoint_path.resolve() if checkpoint_path is not None else None

    if not tif_path.exists():
        raise FileNotFoundError(f"GeoTIFF not found at {tif_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model weights not found at {model_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tiles_dir.mkdir(parents=True, exist_ok=True)
    if checkpoint_path is not None:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    tile_records = tile_sar(str(tif_path), str(tiles_dir), tile_size=tile_size)
    detections = detect_tiles(
        str(tiles_dir),
        str(model_path),
        conf_threshold=conf_threshold,
        chunk_size=chunk_size,
        checkpoint_path=str(checkpoint_path) if checkpoint_path is not None else None,
    )
    georeferenced = georeference_detections(detections)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(georeferenced, f, indent=2)

    summary = {
        "tif_path": str(tif_path),
        "model_path": str(model_path),
        "tiles_dir": str(tiles_dir),
        "output_path": str(output_path),
        "checkpoint_path": str(checkpoint_path) if checkpoint_path is not None else None,
        "tile_count": len(tile_records),
        "detection_count": len(georeferenced),
    }
    return summary


def main() -> None:
    args = parse_args()
    summary = run_inference_pipeline(
        tif_path=args.tif_path,
        model_path=args.model_path,
        tiles_dir=args.tiles_dir,
        output_path=args.output_path,
        checkpoint_path=args.checkpoint_path,
        tile_size=args.tile_size,
        conf_threshold=args.conf_threshold,
        chunk_size=args.chunk_size,
    )

    print(f"Tiles written: {summary['tile_count']}")
    print(f"Detections written: {summary['detection_count']}")
    print(f"Output path: {summary['output_path']}")


if __name__ == "__main__":
    main()
