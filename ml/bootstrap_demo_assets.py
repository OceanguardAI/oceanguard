"""Create local demo assets so the ML pipeline can run without external files."""
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"

BAR_REEF_POLYGON = {
    "type": "Feature",
    "properties": {
        "NAME": "Bar Reef Marine Sanctuary",
        "WDPAID": 4783,
    },
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [79.73550022, 8.26746323],
                [79.76349894, 8.32294782],
                [79.78222715, 8.53409068],
                [79.68343578, 8.53142862],
                [79.68286497, 8.26487243],
                [79.73550022, 8.26746323],
            ]
        ],
    },
}

GFW_DEMO = {
    "entries": [
        {"lat": 8.66, "lon": 79.75, "timestamp": "2026-06-09T06:12:00Z", "matched": False},
        {"lat": 8.48, "lon": 79.58, "timestamp": "2026-06-09T10:44:00Z", "matched": False},
        {"lat": 8.51, "lon": 79.68, "timestamp": "2026-06-09T14:32:00Z", "matched": False},
        {"lat": 8.68, "lon": 79.69, "timestamp": "2026-06-09T18:05:00Z", "matched": False},
    ]
}

PORTS_DEMO = {
    "version": 0.6,
    "elements": [
        {
            "type": "node",
            "id": 123456789,
            "lat": 8.2155202,
            "lon": 79.7061466,
            "tags": {
                "leisure": "marina",
                "name": "Marina (OSM)",
            },
        }
    ],
}

YOLO_DEMO = [
    {
        "tile": "tiles/tile_r0000_c0000.png",
        "row_off": 0,
        "col_off": 0,
        "x_center_px": 312.4,
        "y_center_px": 198.7,
        "width_px": 45.2,
        "height_px": 22.8,
        "confidence": 0.76,
        "class_id": 0,
        "lat": 7.234567,
        "lon": 4.567890,
    },
    {
        "tile": "tiles/tile_r0640_c1280.png",
        "row_off": 640,
        "col_off": 1280,
        "x_center_px": 221.9,
        "y_center_px": 330.1,
        "width_px": 38.4,
        "height_px": 18.2,
        "confidence": 0.63,
        "class_id": 0,
        "lat": 7.241111,
        "lon": 4.574321,
    },
    {
        "tile": "tiles/tile_r1280_c0640.png",
        "row_off": 1280,
        "col_off": 640,
        "x_center_px": 144.3,
        "y_center_px": 410.8,
        "width_px": 29.6,
        "height_px": 16.5,
        "confidence": 0.51,
        "class_id": 0,
        "lat": 7.248888,
        "lon": 4.581234,
    },
]


def _write_json_if_missing(path: Path, payload: object) -> bool:
    if path.exists():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return True


def main() -> None:
    created = []

    if _write_json_if_missing(DATA_DIR / "bar_reef.geojson", BAR_REEF_POLYGON):
        created.append("data/bar_reef.geojson")
    if _write_json_if_missing(DATA_DIR / "gfw_bar_reef_sar_unmatched.json", GFW_DEMO):
        created.append("data/gfw_bar_reef_sar_unmatched.json")
    if _write_json_if_missing(DATA_DIR / "overpass_bar_reef_ports.json", PORTS_DEMO):
        created.append("data/overpass_bar_reef_ports.json")
    if _write_json_if_missing(OUTPUTS_DIR / "detections_scene1_georef.json", YOLO_DEMO):
        created.append("outputs/detections_scene1_georef.json")

    if created:
        print("Created demo ML assets:")
        for item in created:
            print(f"  - {item}")
    else:
        print("No demo assets created; all target files already exist.")


if __name__ == "__main__":
    main()
