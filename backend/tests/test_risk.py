from pipeline.risk import calculate_risk


def test_bar_reef_003_exact() -> None:
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


def test_inside_mpa_raises_score() -> None:
    score, level = calculate_risk(
        detection_conf=0.70,
        ais_matched=False,
        ais_data_available=True,
        inside_mpa=True,
        near_mpa=False,
        image_quality_score=1.0,
    )
    assert score > 0.61
    assert level in {"HIGH", "CRITICAL"}


def test_ais_matched_reduces_score() -> None:
    score_unmatched, _ = calculate_risk(0.70, False, True, False, False, 1.0)
    score_matched, _ = calculate_risk(0.70, True, True, False, False, 1.0)
    assert score_matched < score_unmatched


def test_no_ais_data_neutral() -> None:
    score, level = calculate_risk(0.70, False, False, False, False, 1.0)
    assert score == 0.285
    assert level == "LOW"
