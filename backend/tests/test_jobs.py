from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

from app.jobs.cli import run_once
from app.jobs.queue import ClaimedJob, daily_gfw_key, retry_delay_seconds


def test_retry_delay_is_bounded() -> None:
    assert [retry_delay_seconds(n) for n in (1, 2, 3, 20)] == [60, 120, 240, 3600]


def test_daily_key_uses_utc_day() -> None:
    assert daily_gfw_key(datetime(2026, 9, 25, tzinfo=timezone.utc)) == "gfw-refresh:2026-09-25"


def test_worker_does_not_fetch_without_claim() -> None:
    queue = Mock()
    queue.claim.return_value = None
    with patch("app.jobs.cli.gfw_ingest.fetch_activity") as fetch:
        assert run_once(queue, Mock()) == "idle"
    fetch.assert_not_called()


def test_worker_marks_provider_failure_without_replacing_snapshot() -> None:
    job = ClaimedJob(uuid4(), "gfw_refresh", uuid4(), 1)
    queue = Mock()
    queue.claim.return_value = job
    queue.fail.return_value = True
    activity = Mock()
    with patch("app.jobs.cli.gfw_ingest.fetch_activity", side_effect=ValueError("bad response")):
        assert run_once(queue, activity) == "retry"
    queue.fail.assert_called_once_with(job, "invalid_response")
    queue.complete_gfw.assert_not_called()
    activity.replace.assert_not_called()


def test_worker_completes_only_after_fetch() -> None:
    job = ClaimedJob(uuid4(), "gfw_refresh", uuid4(), 1)
    queue = Mock()
    queue.claim.return_value = job
    queue.complete_gfw.return_value = True
    activity = Mock()
    with patch("app.jobs.cli.gfw_ingest.fetch_activity", return_value=[]) as fetch:
        assert run_once(queue, activity) == "succeeded"
    fetch.assert_called_once()
    queue.complete_gfw.assert_called_once_with(job, activity, [])


def test_worker_reports_storage_failure_separately() -> None:
    job = ClaimedJob(uuid4(), "gfw_refresh", uuid4(), 1)
    queue = Mock()
    queue.claim.return_value = job
    queue.complete_gfw.side_effect = OSError("database unavailable")
    queue.fail.return_value = True
    with patch("app.jobs.cli.gfw_ingest.fetch_activity", return_value=[]):
        assert run_once(queue, Mock()) == "retry"
    queue.fail.assert_called_once_with(job, "storage_unavailable")
