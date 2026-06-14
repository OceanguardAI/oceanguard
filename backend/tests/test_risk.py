"""Tests for the risk scoring formula. Imports from ml pipeline."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ml"))

from pipeline.risk import calculate_risk


def test_bar_reef_003_exact():
    """Canonical case — must yield exactly 0.61 / HIGH."""
    score, level = calculate_risk(
        detection_conf=0.70,
        ais_matched=False,
        ais_data_available=True,
        inside_mpa=False,
        near_mpa=True,
        image_quality_score=1.0,
    )
    assert score == 0.61, f"Expected 0.61, got {score}"
    assert level == "HIGH", f"Expected HIGH, got {level}"


def test_inside_mpa_raises_score():
    score, level = calculate_risk(
        detection_conf=0.70, ais_matched=False, ais_data_available=True,
        inside_mpa=True, near_mpa=False, image_quality_score=1.0,
    )
    assert score > 0.61
    assert level in ("HIGH", "CRITICAL")


def test_ais_matched_reduces_score():
    score_un, _ = calculate_risk(0.70, False, True, False, False, 1.0)
    score_ma, _ = calculate_risk(0.70, True,  True, False, False, 1.0)
    assert score_ma < score_un


def test_no_ais_data_neutral():
    score, level = calculate_risk(0.70, False, False, False, False, 1.0)
    # ais_score=0.3 (neutral), mpa_score=0 -> risk = 0.21 + 0.075 = 0.285
    assert score == 0.285
    assert level == "LOW"


def test_degraded_image_reduces_score():
    full, _ = calculate_risk(0.70, False, True, False, True, 1.0)
    half, _ = calculate_risk(0.70, False, True, False, True, 0.5)
    assert half < full


def test_critical_threshold():
    _, level = calculate_risk(1.0, False, True, True, False, 1.0,
                              fishing_score=1.0, repeated_activity_score=1.0)
    assert level == "CRITICAL"


def test_low_threshold():
    _, level = calculate_risk(0.10, True, True, False, False, 1.0)
    assert level == "LOW"
