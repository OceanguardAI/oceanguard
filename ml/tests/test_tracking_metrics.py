from evaluation.tracking_metrics import evaluate_tracking


def test_tracking_metrics_reward_consistent_identity():
    truth = [
        {"frame_id": "1", "gt_id": "vessel-1", "x_center_px": 10, "y_center_px": 10},
        {"frame_id": "2", "gt_id": "vessel-1", "x_center_px": 20, "y_center_px": 10},
    ]
    predictions = [
        {"frame_id": "1", "track_id": "track-1", "x_center_px": 11, "y_center_px": 10},
        {"frame_id": "2", "track_id": "track-1", "x_center_px": 21, "y_center_px": 10},
    ]
    metrics = evaluate_tracking(truth, predictions, max_distance_px=3)
    assert metrics.idf1 == 1.0
    assert metrics.identity_switches == 0
    assert metrics.detection_recall == 1.0


def test_tracking_metrics_expose_identity_switch_and_gap():
    truth = [
        {"frame_id": "1", "gt_id": "vessel-1", "x_center_px": 10, "y_center_px": 10},
        {"frame_id": "3", "gt_id": "vessel-1", "x_center_px": 30, "y_center_px": 10},
    ]
    predictions = [
        {"frame_id": "1", "track_id": "track-1", "x_center_px": 10, "y_center_px": 10},
        {"frame_id": "3", "track_id": "track-2", "x_center_px": 30, "y_center_px": 10},
    ]
    metrics = evaluate_tracking(truth, predictions, max_distance_px=1)
    assert metrics.identity_switches == 1
    assert metrics.fragmentation == 1
    assert metrics.idf1 == 0.5
