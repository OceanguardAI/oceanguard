"""Smoke-check a trained YOLO model artifact."""
from __future__ import annotations

import argparse
from pathlib import Path

from build_risk_events import DEFAULT_SOURCE_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a trained YOLO model artifact.")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=DEFAULT_SOURCE_ROOT / "models" / "best.pt",
        help="Path to the YOLO weights file.",
    )
    return parser.parse_args()


def inspect_model(model_path: Path) -> dict:
    """Load a YOLO model and return a compact summary."""
    resolved = model_path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Model not found at {resolved}")

    try:
        from ultralytics import YOLO
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise ImportError(
            "ultralytics is required for validate_model.py. Install ml/requirements.txt first."
        ) from exc

    model = YOLO(str(resolved))
    class_names = getattr(model.model, "names", {}) or {}
    summary = {
        "model_path": str(resolved),
        "size_bytes": resolved.stat().st_size,
        "model_type": type(model.model).__name__,
        "class_count": len(class_names),
        "class_names": class_names,
        "task": getattr(model, "task", None),
    }
    return summary


def main() -> None:
    args = parse_args()
    summary = inspect_model(args.model_path)
    print(f"Model path: {summary['model_path']}")
    print(f"Model size (bytes): {summary['size_bytes']}")
    print(f"Model type: {summary['model_type']}")
    print(f"Task: {summary['task']}")
    print(f"Class count: {summary['class_count']}")
    print(f"Class names: {summary['class_names']}")


if __name__ == "__main__":
    main()
