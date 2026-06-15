from pipeline.risk import calculate_risk


def test_bar_reef_003_example_matches_docs():
    score, level = calculate_risk(
        detection_conf=0.70,
        ais_matched=False,
        ais_data_available=True,
        inside_mpa=False,
        near_mpa=True,
        image_quality_score=1.0,
    )

    assert score == 0.61
    assert level == "HIGH"


def test_missing_ais_data_stays_neutral_not_guilty():
    score, level = calculate_risk(
        detection_conf=0.50,
        ais_matched=False,
        ais_data_available=False,
        inside_mpa=False,
        near_mpa=False,
        image_quality_score=1.0,
    )

    assert score == 0.225
    assert level == "LOW"
