"""Risk scoring engine — exact formula from BUILD_PLAN.md. DO NOT MODIFY."""


def calculate_risk(
    detection_conf: float,
    ais_matched: bool,
    ais_data_available: bool,
    inside_mpa: bool,
    near_mpa: bool,
    image_quality_score: float,  # 0..1
    fishing_score: float = 0.0,
    repeated_activity_score: float = 0.0,
) -> tuple[float, str]:
    """Deterministic risk scoring formula.

    Weights:
        0.30 * effective_conf   (SAR detection confidence × image quality)
        0.25 * ais_score        (1.0 if unmatched+available, 0.3 if unavailable, 0.0 if matched)
        0.25 * mpa_score        (1.0 inside, 0.6 near ≤5km, 0.0 otherwise)
        0.10 * fishing_score
        0.10 * repeated_activity_score

    Returns:
        (risk_score rounded to 3dp, risk_level string)
    """
    effective_conf = detection_conf * image_quality_score

    if not ais_data_available:
        ais_score = 0.3        # neutral — absence of data ≠ guilt
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
