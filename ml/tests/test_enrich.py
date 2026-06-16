import json

import pytest

from pipeline.enrich import classify_mpa, distance_to_mpa, load_mpa, nearest_port_distance


def test_bar_reef_reference_points_match_expected_ranges(tmp_path):
    mpa_path = tmp_path / "bar_reef.geojson"
    ports_path = tmp_path / "ports.json"

    mpa_payload = {
        "type": "Feature",
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
        "properties": {"NAME": "Bar Reef Marine Sanctuary"},
    }
    ports_payload = {
        "elements": [
            {
                "lat": 8.2155202,
                "lon": 79.7061466,
                "tags": {"name": "Marina (OSM)"},
            }
        ]
    }

    mpa_path.write_text(json.dumps(mpa_payload), encoding="utf-8")
    ports_path.write_text(json.dumps(ports_payload), encoding="utf-8")

    mpa = load_mpa(mpa_path)

    near_distance = distance_to_mpa(8.51, 79.68, mpa)
    far_distance = distance_to_mpa(8.66, 79.75, mpa)
    inside, near = classify_mpa(near_distance)
    port_distance, port_name = nearest_port_distance(8.51, 79.68, ports_path)

    assert near_distance == pytest.approx(0.37, abs=0.02)
    assert far_distance == pytest.approx(14.09, abs=0.05)
    assert inside is False
    assert near is True
    assert port_distance == pytest.approx(32.9, abs=0.1)
    assert port_name == "Marina (OSM)"


def test_nearest_port_distance_returns_none_when_port_data_is_empty(tmp_path):
    ports_path = tmp_path / "ports.json"
    ports_path.write_text(json.dumps({"elements": []}), encoding="utf-8")

    distance, name = nearest_port_distance(8.51, 79.68, ports_path)

    assert distance is None
    assert name is None
