"""Deterministic, uncertainty-aware observation-to-AIS association."""
from __future__ import annotations

import math
from datetime import timezone
from hashlib import sha256
from typing import Iterable

from app.models.schemas import AISMessageRecord, AssociationRecord, ObservationRecord


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    value = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(value))


def _score(
    observation: ObservationRecord,
    message: AISMessageRecord,
    max_time_seconds: int,
    max_distance_km: float,
) -> tuple[float, list[str]]:
    time_delta = abs(
        (observation.observed_at.astimezone(timezone.utc)
         - message.message_at.astimezone(timezone.utc)).total_seconds()
    )
    distance = haversine_km(observation.lat, observation.lon, message.lat, message.lon)
    reasons: list[str] = []
    if time_delta > max_time_seconds:
        reasons.append("outside_time_window")
    if distance > max_distance_km:
        reasons.append("outside_distance_window")
    if reasons:
        return 0.0, reasons
    time_score = 1.0 - time_delta / max_time_seconds
    distance_score = 1.0 - distance / max_distance_km
    return round(max(0.0, 0.55 * time_score + 0.45 * distance_score), 6), []


def associate_observation(
    observation: ObservationRecord,
    messages: Iterable[AISMessageRecord],
    *,
    coverage_available: bool,
    method_version: str = "distance-time-v1",
    max_time_seconds: int = 900,
    max_distance_km: float = 5.0,
    minimum_score: float = 0.55,
    ambiguity_margin: float = 0.08,
) -> AssociationRecord:
    """Return one auditable decision and retain rejection reasons.

    coverage_available comes from the source adapter. An empty list with
    unavailable coverage is not equivalent to a clean unmatched result.
    """
    if max_time_seconds <= 0 or max_distance_km <= 0:
        raise ValueError("association windows must be positive")
    candidates: list[tuple[AISMessageRecord, float]] = []
    rejection_reasons: list[str] = []
    for message in messages:
        score, reasons = _score(observation, message, max_time_seconds, max_distance_km)
        if reasons:
            rejection_reasons.extend(f"{message.mmsi}:{reason}" for reason in reasons)
        else:
            candidates.append((message, score))

    candidates.sort(key=lambda item: (-item[1], item[0].mmsi, item[0].id))
    if not coverage_available:
        decision = "unavailable"
        selected = None
        score = 0.0
        rejection_reasons.append("ais_coverage_unavailable")
    elif not candidates or candidates[0][1] < minimum_score:
        decision = "unmatched"
        selected = None
        score = candidates[0][1] if candidates else 0.0
        rejection_reasons.append("no_candidate_above_threshold")
    elif len(candidates) > 1 and candidates[0][1] - candidates[1][1] < ambiguity_margin:
        decision = "ambiguous"
        selected = None
        score = candidates[0][1]
        rejection_reasons.append("top_candidates_too_close")
    else:
        decision = "matched"
        selected = candidates[0][0]
        score = candidates[0][1]

    digest = sha256(
        f"{method_version}|{observation.id}|{selected.id if selected else decision}".encode()
    ).hexdigest()[:24]
    return AssociationRecord(
        id=f"assoc-{digest}",
        observation_id=observation.id,
        ais_message_id=selected.id if selected else None,
        score=score,
        decision=decision,
        method_version=method_version,
        rejection_reasons=sorted(set(rejection_reasons)),
    )
