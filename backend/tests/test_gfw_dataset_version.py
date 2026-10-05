"""GFW dataset-version handling (data pipeline v4 -> v5 transition).

``public-global-sar-presence:latest`` is an alias GFW re-points when a new
pipeline version becomes the default. These tests pin the behaviour that keeps
results attributable to the version that actually produced them.
"""
from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

from app.core.config import settings
from app.services import gfw_ingest


def _client_returning(payload: dict) -> MagicMock:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    client = MagicMock()
    client.post.return_value = response
    client.__enter__.return_value = client
    return client


def test_default_dataset_is_pinned_and_latest_alias_still_honoured() -> None:
    assert settings.gfw_sar_dataset == "public-global-sar-presence:v4.0"
    assert gfw_ingest.DEFAULT_SAR_DATASET == "public-global-sar-presence:v4.0"
    with patch.object(settings, "gfw_sar_dataset", "public-global-sar-presence:latest"):
        assert gfw_ingest.requested_dataset() == "public-global-sar-presence:latest"


def test_requested_dataset_can_be_pinned_and_blank_falls_back() -> None:
    with patch.object(settings, "gfw_sar_dataset", "  public-global-sar-presence:v5.0 "):
        assert gfw_ingest.requested_dataset() == "public-global-sar-presence:v5.0"
    with patch.object(settings, "gfw_sar_dataset", "   "):
        assert gfw_ingest.requested_dataset() == gfw_ingest.DEFAULT_SAR_DATASET


def test_pinned_dataset_is_sent_to_gfw() -> None:
    client = _client_returning({"entries": []})
    with patch.object(settings, "gfw_sar_dataset", "public-global-sar-presence:v4.0"), \
            patch.object(settings, "gfw_api_token", "test-token"), \
            patch.object(gfw_ingest.httpx, "Client", return_value=client):
        gfw_ingest._fetch_sar_report()
    assert client.post.call_args.kwargs["params"]["datasets[0]"] == "public-global-sar-presence:v4.0"


def test_resolved_dataset_version_is_recorded_when_alias_requested() -> None:
    payload = {"entries": [{"public-global-sar-presence:v5.0": [
        {"lat": 8.5, "lon": 79.6, "detections": 2},
    ]}]}
    client = _client_returning(payload)
    with patch.object(settings, "gfw_sar_dataset", "public-global-sar-presence:latest"), \
            patch.object(settings, "gfw_api_token", "test-token"), \
            patch.object(gfw_ingest.httpx, "Client", return_value=client):
        activity = gfw_ingest.fetch_activity()
    assert [cell.dataset for cell in activity] == ["public-global-sar-presence:v5.0"]


def test_flat_rows_fall_back_to_requested_dataset() -> None:
    payload = {"entries": [{"lat": 8.5, "lon": 79.6, "detections": 2}]}
    client = _client_returning(payload)
    with patch.object(settings, "gfw_sar_dataset", "public-global-sar-presence:v4.0"), \
            patch.object(settings, "gfw_api_token", "test-token"), \
            patch.object(gfw_ingest.httpx, "Client", return_value=client):
        activity = gfw_ingest.fetch_activity()
    assert [cell.dataset for cell in activity] == ["public-global-sar-presence:v4.0"]


def test_same_cell_from_v4_and_v5_never_collapses_to_one_record() -> None:
    cell = {"lat": 8.5, "lon": 79.6, "detections": 2}
    ids = {}
    for version in ("v4.0", "v5.0"):
        payload = {"entries": [{f"public-global-sar-presence:{version}": [cell]}]}
        client = _client_returning(payload)
        with patch.object(settings, "gfw_sar_dataset", "public-global-sar-presence:latest"), \
                patch.object(settings, "gfw_api_token", "test-token"), \
                patch.object(gfw_ingest.httpx, "Client", return_value=client):
            ids[version] = gfw_ingest.fetch_activity()[0].id
    assert ids["v4.0"] != ids["v5.0"]


def test_non_dataset_group_keys_are_not_recorded_as_dataset() -> None:
    payload = {"entries": [{"someGroup": [{"lat": 1.0, "lon": 2.0, "detections": 1}]}]}
    client = _client_returning(payload)
    with patch.object(settings, "gfw_sar_dataset", "public-global-sar-presence:v4.0"), \
            patch.object(settings, "gfw_api_token", "test-token"), \
            patch.object(gfw_ingest.httpx, "Client", return_value=client):
        activity = gfw_ingest.fetch_activity()
    assert activity[0].dataset == "public-global-sar-presence:v4.0"
