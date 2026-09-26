"""Explainable alert policy built on deterministic evidence states."""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from app.models.schemas import AlertRecord, AssociationRecord


def association_alert(
    *,
    association: AssociationRecord,
    occurred_at: datetime,
    zone_id: str | None = None,
    rule_version: str = "association-review-v1",
) -> AlertRecord | None:
    """Create a review candidate only when the source state supports one.

    Unavailable AIS produces no alert: there is not enough evidence. Unmatched
    and ambiguous states can produce review candidates, but neither is labeled
    as illegal activity or deliberate AIS disabling.
    """
    if association.decision in {"unavailable", "matched"}:
        return None

    severity = "medium" if association.decision == "unmatched" else "low"
    uncertainty = (
        "AIS coverage was available but no candidate met the configured "
        "time-distance threshold; this does not prove deliberate non-broadcast."
        if association.decision == "unmatched"
        else "Multiple AIS candidates remain plausible; identity assignment is abstained."
    )
    scope = zone_id or "open-water"
    dedupe_key = f"{rule_version}:{association.observation_id}:{scope}:{association.decision}"
    alert_id = "alert-" + sha256(dedupe_key.encode()).hexdigest()[:24]
    return AlertRecord(
        id=alert_id,
        rule_version=rule_version,
        severity=severity,
        starts_at=occurred_at,
        uncertainty=uncertainty,
        dedupe_key=dedupe_key,
        observation_ids=[association.observation_id],
        association_ids=[association.id],
    )
