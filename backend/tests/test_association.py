from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.schemas import AISMessageRecord, ObservationRecord
from app.services.alerts import association_alert
from app.services.association import associate_observation


NOW = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)


def observation() -> ObservationRecord:
    return ObservationRecord(
        id="obs-1", source_id="sentinel-1", observed_at=NOW,
        ingested_at=NOW, lat=8.5, lon=79.6,
    )


def ais(mmsi: str, seconds: int = 0, lon: float = 79.6) -> AISMessageRecord:
    return AISMessageRecord(
        id=f"ais-{mmsi}", mmsi=mmsi, message_at=NOW + timedelta(seconds=seconds),
        received_at=NOW, lat=8.5, lon=lon,
    )


def test_empty_ais_with_unavailable_coverage_is_not_unmatched() -> None:
    result = associate_observation(observation(), [], coverage_available=False)
    assert result.decision == "unavailable"
    assert association_alert(association=result, occurred_at=NOW) is None


def test_usable_ais_without_candidate_is_unmatched() -> None:
    result = associate_observation(observation(), [ais("1", lon=80.0)], coverage_available=True)
    assert result.decision == "unmatched"
    alert = association_alert(association=result, occurred_at=NOW, zone_id="mpa-1")
    assert alert is not None
    assert "does not prove" in alert.uncertainty


def test_close_candidates_are_ambiguous() -> None:
    result = associate_observation(observation(), [ais("1"), ais("2")], coverage_available=True)
    assert result.decision == "ambiguous"
    assert result.ais_message_id is None


def test_one_clear_candidate_is_matched() -> None:
    result = associate_observation(
        observation(), [ais("1"), ais("2", seconds=300)], coverage_available=True
    )
    assert result.decision == "matched"
    assert result.ais_message_id == "ais-1"
