import json

import build_risk_events as builder


def test_build_events_returns_expected_shape(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()

    (data_dir / "bar_reef.geojson").write_text(
        json.dumps(
            {
                "type": "Feature",
                "properties": {"NAME": "Bar Reef Marine Sanctuary"},
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
        ),
        encoding="utf-8",
    )
    (data_dir / "gfw_bar_reef_sar_unmatched.json").write_text(
        json.dumps({"entries": builder.DEFAULT_GFW_ENTRIES}),
        encoding="utf-8",
    )
    (data_dir / "overpass_bar_reef_ports.json").write_text(
        json.dumps(
            {
                "elements": [
                    {
                        "lat": 8.2155202,
                        "lon": 79.7061466,
                        "tags": {"name": "Marina (OSM)"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (outputs_dir / "detections_scene1_georef.json").write_text(
        json.dumps(
            [
                {"lat": 7.23, "lon": 4.56, "confidence": 0.76},
                {"lat": 7.24, "lon": 4.57, "confidence": 0.51},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(builder, "DATA_DIR", data_dir)
    monkeypatch.setattr(builder, "OUTPUTS_DIR", outputs_dir)

    events = builder.build_events()

    assert len(events) == 6
    assert sum(1 for event in events if event["source"] == "GFW") == 4
    assert sum(1 for event in events if event["source"] == "YOLO_SAR") == 2

    bar_reef_003 = next(event for event in events if event["id"] == "bar-reef-003")
    assert bar_reef_003["risk_score"] == 0.61
    assert bar_reef_003["risk_level"] == "HIGH"
    assert bar_reef_003["near_mpa"] is True

    required_fields = {
        "id",
        "source",
        "lat",
        "lon",
        "risk_score",
        "risk_level",
        "sar_confidence",
        "image_quality",
        "ais_matched",
        "ais_data_available",
        "matching_method",
        "inside_mpa",
        "near_mpa",
        "mpa_name",
        "distance_to_mpa_km",
        "distance_from_port_km",
        "nearest_port",
        "timestamp",
        "review_status",
        "why_flagged",
        "uncertainty",
        "confidence_threshold",
        "recommended_action",
        "thumbnail",
    }
    assert required_fields.issubset(events[0].keys())
