import json

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

    assert 0.2 <= near_distance <= 1.0
    assert far_distance > 5.0
    assert inside is False
    assert near is True
    assert 30.0 <= port_distance <= 40.0
    assert port_name == "Marina (OSM)"
