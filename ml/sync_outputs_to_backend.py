"""Copy ML pipeline outputs into backend/data for handoff."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync generated ML outputs into backend/data.")
    parser.add_argument(
        "--risk-events",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs" / "risk_events.json",
        help="Path to generated risk_events.json",
    )
    parser.add_argument(
        "--bar-reef-geojson",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "bar_reef.geojson",
        help="Path to the source bar_reef.geojson",
    )
    parser.add_argument(
        "--backend-data-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "backend" / "data",
        help="Destination backend/data directory.",
    )
    return parser.parse_args()


def sync_outputs(
    risk_events: Path,
    bar_reef_geojson: Path,
    backend_data_dir: Path,
) -> tuple[Path, Path]:
    """Copy ML outputs into backend/data and return destination paths."""
    backend_data_dir = backend_data_dir.resolve()
    backend_data_dir.mkdir(parents=True, exist_ok=True)

    if not risk_events.exists():
        raise FileNotFoundError(f"risk_events.json not found at {risk_events}")
    if not bar_reef_geojson.exists():
        raise FileNotFoundError(f"bar_reef.geojson not found at {bar_reef_geojson}")

    risk_dest = backend_data_dir / "risk_events.json"
    geo_dest = backend_data_dir / "bar_reef.geojson"

    shutil.copy2(risk_events, risk_dest)
    shutil.copy2(bar_reef_geojson, geo_dest)
    return risk_dest, geo_dest


def main() -> None:
    args = parse_args()
    risk_dest, geo_dest = sync_outputs(
        args.risk_events,
        args.bar_reef_geojson,
        args.backend_data_dir,
    )

    print(f"Copied risk events to: {risk_dest}")
    print(f"Copied Bar Reef geojson to: {geo_dest}")


if __name__ == "__main__":
    main()
