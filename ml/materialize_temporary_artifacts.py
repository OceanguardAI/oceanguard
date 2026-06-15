"""Copy temporary ML cache artifacts into the standard ml/ workspace layout."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from build_risk_events import DEFAULT_SOURCE_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy cached ML artifacts from ml/Temprary/ml into the standard ml/ layout."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEFAULT_SOURCE_ROOT,
        help="Temporary artifact root containing data/, models/, and outputs/ folders.",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Destination ml/ root to populate.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing destination files.",
    )
    return parser.parse_args()


def materialize_artifacts(
    source_root: Path,
    target_root: Path,
    overwrite: bool = False,
) -> dict:
    """Copy known ML artifact files into the standard workspace layout."""
    source_root = source_root.resolve()
    target_root = target_root.resolve()

    file_map = {
        source_root / "data" / "bar_reef.geojson": target_root / "data" / "bar_reef.geojson",
        source_root
        / "data"
        / "gfw_bar_reef_sar_unmatched.json": target_root / "data" / "gfw_bar_reef_sar_unmatched.json",
        source_root
        / "data"
        / "overpass_bar_reef_ports.json": target_root / "data" / "overpass_bar_reef_ports.json",
        source_root / "models" / "best.pt": target_root / "models" / "best.pt",
        source_root
        / "outputs"
        / "detections_scene1_georef.json": target_root / "outputs" / "detections_scene1_georef.json",
    }

    copied: list[str] = []
    skipped: list[str] = []

    for src, dst in file_map.items():
        if not src.exists():
            raise FileNotFoundError(f"Required source artifact missing: {src}")

        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and not overwrite:
            skipped.append(str(dst))
            continue

        shutil.copy2(src, dst)
        copied.append(str(dst))

    return {
        "source_root": str(source_root),
        "target_root": str(target_root),
        "copied": copied,
        "skipped": skipped,
    }


def main() -> None:
    args = parse_args()
    summary = materialize_artifacts(
        source_root=args.source_root,
        target_root=args.target_root,
        overwrite=args.overwrite,
    )
    print(f"Source root: {summary['source_root']}")
    print(f"Target root: {summary['target_root']}")
    print(f"Copied files: {len(summary['copied'])}")
    for item in summary["copied"]:
        print(f"  copied: {item}")
    if summary["skipped"]:
        print(f"Skipped files: {len(summary['skipped'])}")
        for item in summary["skipped"]:
            print(f"  skipped: {item}")


if __name__ == "__main__":
    main()
