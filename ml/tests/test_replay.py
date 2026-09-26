import json

import pytest

from pipeline.replay import replay_sequence


def test_replay_sequence_returns_json_ready_points():
    points = replay_sequence(
        [
            {
                "frame_id": "1",
                "observed_at": "2026-09-26T10:00:00Z",
                "detections": [{"x_center_px": 10, "y_center_px": 10}],
            },
            {
                "frame_id": "2",
                "observed_at": "2026-09-26T10:00:01Z",
                "detections": [],
            },
        ]
    )
    assert len(points) == 2
    assert points[1]["is_predicted"] is True
    json.dumps(points)


def test_replay_rejects_unordered_frames():
    with pytest.raises(ValueError, match="ordered"):
        replay_sequence(
            [
                {"frame_id": "2", "observed_at": "2026-09-26T10:00:01Z", "detections": []},
                {"frame_id": "1", "observed_at": "2026-09-26T10:00:00Z", "detections": []},
            ]
        )


def test_replay_rejects_timezone_free_frames():
    with pytest.raises(ValueError, match="timezone"):
        replay_sequence([{"frame_id": "1", "observed_at": "2026-09-26T10:00:00", "detections": []}])
