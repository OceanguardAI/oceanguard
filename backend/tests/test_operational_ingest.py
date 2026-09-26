from datetime import datetime, timedelta, timezone

from app.models.schemas import AISMessageRecord, ObservationRecord
from app.services.operational_ingest import persist_observation_bundle


class FakeStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def insert_observation(self, record):
        self.calls.append(("observation", record.id))
        return record

    def insert_ais(self, record):
        self.calls.append(("ais", record.id))
        return record

    def insert_association(self, record):
        self.calls.append(("association", record.id))
        return record

    def insert_alert(self, record):
        self.calls.append(("alert", record.id))
        return record


def _observation() -> ObservationRecord:
    observed_at = datetime(2026, 9, 26, 10, tzinfo=timezone.utc)
    return ObservationRecord(
        id="obs-1",
        source_id="sar:test",
        observed_at=observed_at,
        ingested_at=observed_at + timedelta(minutes=1),
        lat=6.0,
        lon=80.0,
        model_version="baseline-v1",
    )


def _ais(message_id: str, offset_seconds: int, lon: float = 80.0) -> AISMessageRecord:
    observed_at = _observation().observed_at
    return AISMessageRecord(
        id=message_id,
        mmsi=message_id,
        message_at=observed_at + timedelta(seconds=offset_seconds),
        received_at=observed_at + timedelta(seconds=offset_seconds + 1),
        lat=6.0,
        lon=lon,
    )


def test_persist_bundle_writes_unmatched_review_candidate():
    store = FakeStore()
    result = persist_observation_bundle(
        store,
        _observation(),
        [_ais("mmsi-2", 10, lon=80.06)],
        ais_coverage_available=True,
        zone_id="mpa-1",
    )
    assert result.association.decision == "unmatched"
    assert result.alert is not None
    assert [kind for kind, _ in store.calls] == ["observation", "ais", "association", "alert"]


def test_persist_bundle_does_not_alert_when_ais_coverage_is_unavailable():
    store = FakeStore()
    result = persist_observation_bundle(
        store,
        _observation(),
        [],
        ais_coverage_available=False,
    )
    assert result.association.decision == "unavailable"
    assert result.alert is None
    assert [kind for kind, _ in store.calls] == ["observation", "association"]


def test_persist_bundle_is_repeatable_for_same_input():
    first_store = FakeStore()
    second_store = FakeStore()
    first = persist_observation_bundle(
        first_store, _observation(), [_ais("mmsi-1", 10, lon=80.06)], ais_coverage_available=True
    )
    second = persist_observation_bundle(
        second_store, _observation(), [_ais("mmsi-1", 10, lon=80.06)], ais_coverage_available=True
    )
    assert first.association.id == second.association.id
    assert first.alert is not None and second.alert is not None
    assert first.alert.id == second.alert.id
