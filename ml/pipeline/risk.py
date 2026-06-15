"""Deterministic risk scoring engine. Formula is fixed — changes require updating
docs/data-dictionary.md and test_risk.py."""

from __future__ import annotations


def calculate_risk(
    detection_conf: float,
    ais_matched: bool,
    ais_data_available: bool,
    inside_mpa: bool,
    near_mpa: bool,
    image_quality_score: float,
    fishing_score: float = 0.0,
    repeated_activity_score: float = 0.0,
) -> tuple[float, str]:
    """Return (risk_score, risk_level) for a single detection.

    AIS matching rule: spatial <= 2 km + time window +/- 3 h.
    Near-MPA threshold: <= 5 km from MPA boundary.
    """
    effective_conf = detection_conf * image_quality_score

    if not ais_data_available:
        ais_score = 0.3  # neutral — absence of data != guilt
    else:
        ais_score = 0.0 if ais_matched else 1.0

    mpa_score = 1.0 if inside_mpa else (0.6 if near_mpa else 0.0)

    risk = (
        0.30 * effective_conf
        + 0.25 * ais_score
        + 0.25 * mpa_score
        + 0.10 * fishing_score
        + 0.10 * repeated_activity_score
    )

    if risk >= 0.75:
        level = "CRITICAL"
    elif risk >= 0.55:
        level = "HIGH"
    elif risk >= 0.35:
        level = "MEDIUM"
    else:
        level = "LOW"

    return round(risk, 3), level


if __name__ == "__main__":
    score, level = calculate_risk(
        detection_conf=0.70,
        ais_matched=False,
        ais_data_available=True,
        inside_mpa=False,
        near_mpa=True,
        image_quality_score=1.0,
    )
    print(f"bar-reef-003 example: {score} / {level}")
    assert score == 0.61 and level == "HIGH", f"Unexpected: {score} / {level}"
    print("OK")
