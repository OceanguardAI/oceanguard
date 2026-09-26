"""Persist one observation bundle without collapsing uncertainty."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

from app.models.schemas import (
    AISMessageRecord,
    AlertRecord,
    AssociationRecord,
    ObservationRecord,
)
from app.services.alerts import association_alert
from app.services.association import associate_observation


class OperationalStore(Protocol):
    def insert_observation(self, record: ObservationRecord) -> ObservationRecord: ...

    def insert_ais(self, record: AISMessageRecord) -> AISMessageRecord: ...

    def insert_association(self, record: AssociationRecord) -> AssociationRecord: ...

    def insert_alert(self, record: AlertRecord) -> AlertRecord: ...


@dataclass(frozen=True)
class PersistedObservationBundle:
    observation: ObservationRecord
    association: AssociationRecord
    alert: AlertRecord | None


def persist_observation_bundle(
    store: OperationalStore,
    observation: ObservationRecord,
    ais_messages: Sequence[AISMessageRecord],
    *,
    ais_coverage_available: bool,
    zone_id: str | None = None,
    association_method_version: str = "distance-time-v1",
    alert_rule_version: str = "association-review-v1",
) -> PersistedObservationBundle:
    """Write one observation and its derived records in deterministic order.

    The repository methods use conflict-safe inserts. This function therefore
    can be retried by a durable worker, while the association and alert ids are
    derived from stable inputs and do not accumulate risk on repeat delivery.
    """
    store.insert_observation(observation)
    for message in sorted(ais_messages, key=lambda item: (item.message_at, item.id)):
        store.insert_ais(message)

    association = associate_observation(
        observation,
        ais_messages,
        coverage_available=ais_coverage_available,
        method_version=association_method_version,
    )
    store.insert_association(association)
    alert = association_alert(
        association=association,
        occurred_at=observation.observed_at,
        zone_id=zone_id,
        rule_version=alert_rule_version,
    )
    if alert is not None:
        store.insert_alert(alert)
    return PersistedObservationBundle(observation, association, alert)
