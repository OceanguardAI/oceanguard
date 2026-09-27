from datetime import datetime, timedelta, timezone

from pipeline.tracking import BaselineTracker
import pytest


def test_confirmation_uses_configured_hit_count():
    tracker = BaselineTracker(min_hits=3)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index in range(3):
        points = tracker.update(str(index), start + timedelta(seconds=index),
                                [{"x_center_px": index, "y_center_px": 0}])
        assert points[0].state == ("confirmed" if index == 2 else "tentative")


def test_invalid_frame_does_not_mutate_tracker():
    tracker = BaselineTracker()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tracker.update("1", start, [{"x_center_px": 0, "y_center_px": 0}])
    with pytest.raises(ValueError, match="strictly increasing"):
        tracker.update("old", start - timedelta(seconds=1), [])
    with pytest.raises(ValueError, match="finite"):
        tracker.update("bad", start + timedelta(seconds=1),
                       [{"x_center_px": float("nan"), "y_center_px": 0}])
    points = tracker.update("2", start + timedelta(seconds=1),
                            [{"x_center_px": 1, "y_center_px": 0}])
    assert points[0].track_id == "track-000001"
    assert points[0].state == "confirmed"


def test_tracker_matches_motion_and_confirms_after_two_hits():
    tracker = BaselineTracker(max_match_distance_px=20)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = tracker.update("f1", start, [{"x_center_px": 10, "y_center_px": 10, "confidence": 0.8}])
    second = tracker.update(
        "f2", start + timedelta(seconds=1), [{"x_center_px": 18, "y_center_px": 10, "confidence": 0.9}]
    )
    assert first[0].track_id == second[0].track_id
    assert second[0].state == "confirmed"
    assert second[0].is_predicted is False


def test_tracker_bridges_short_gap_with_prediction():
    tracker = BaselineTracker(max_match_distance_px=20, max_gap_seconds=5)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tracker.update("f1", start, [{"x_center_px": 0, "y_center_px": 0}])
    tracker.update("f2", start + timedelta(seconds=1), [{"x_center_px": 10, "y_center_px": 0}])
    gap = tracker.update("f3", start + timedelta(seconds=2), [])
    assert len(gap) == 1
    assert gap[0].is_predicted is True
    assert gap[0].x_center_px == 20


def test_tracker_expires_after_max_gap_and_new_detection_gets_new_id():
    tracker = BaselineTracker(max_match_distance_px=10, max_gap_seconds=2)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = tracker.update("f1", start, [{"x_center_px": 0, "y_center_px": 0}])
    tracker.update("f2", start + timedelta(seconds=1), [])
    new = tracker.update("f3", start + timedelta(seconds=5), [{"x_center_px": 0, "y_center_px": 0}])
    assert new[0].track_id != first[0].track_id


def test_tracker_deterministically_assigns_nearest_detections():
    tracker = BaselineTracker(max_match_distance_px=50)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = tracker.update(
        "f1", start, [{"x_center_px": 0, "y_center_px": 0}, {"x_center_px": 100, "y_center_px": 0}]
    )
    ids = {point.x_center_px: point.track_id for point in first}
    second = tracker.update(
        "f2",
        start + timedelta(seconds=1),
        [{"x_center_px": 95, "y_center_px": 0}, {"x_center_px": 5, "y_center_px": 0}],
    )
    assert {point.x_center_px: point.track_id for point in second} == {95: ids[100], 5: ids[0]}
