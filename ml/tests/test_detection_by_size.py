from math import inf

import pytest

from evaluation.detection_by_size import (
    DEFAULT_BIN_EDGES_M,
    compare_reports,
    evaluate_by_size,
    wilson_interval,
)


def _scene(truth, predictions, **extra):
    return {"truth": truth, "predictions": predictions, **extra}


def _vessel(x, length):
    return {"x_center_px": x, "y_center_px": 0, "length_m": length}


def _pred(x, conf=0.9):
    return {"x_center_px": x, "y_center_px": 0, "confidence": conf}


def test_recall_is_split_by_vessel_length():
    scene = _scene(
        truth=[_vessel(0, 10), _vessel(50, 10), _vessel(100, 200)],
        predictions=[_pred(100)],  # only the large vessel is found
    )
    report = evaluate_by_size([scene])
    by_label = {b.label: b for b in report.bins}
    assert by_label["0-15 m"].truth == 2 and by_label["0-15 m"].detected == 0
    assert by_label["0-15 m"].recall == 0.0
    assert by_label[">=120 m"].recall == 1.0
    assert report.overall_recall == pytest.approx(1 / 3)


def test_matching_uses_metres_not_pixels():
    # 2 px apart is 20 m at 10 m/px (inside a 30 m radius) but 200 m at 100 m/px.
    near = _scene([_vessel(0, 40)], [_pred(2)], pixel_size_m=10.0)
    far = _scene([_vessel(0, 40)], [_pred(2)], pixel_size_m=100.0)
    assert evaluate_by_size([near]).overall_detected == 1
    assert evaluate_by_size([far]).overall_detected == 0


def test_each_prediction_matches_at_most_one_truth():
    scene = _scene([_vessel(0, 40), _vessel(1, 40)], [_pred(0)])
    report = evaluate_by_size([scene])
    assert report.overall_detected == 1
    assert report.false_positives == 0


def test_false_positives_and_area_rate():
    scene = _scene([_vessel(0, 40)], [_pred(0), _pred(500), _pred(900)], area_km2=50.0)
    report = evaluate_by_size([scene])
    assert report.false_positives == 2
    assert report.precision == pytest.approx(1 / 3)
    assert report.false_positives_per_100km2 == pytest.approx(4.0)


def test_area_rate_omitted_unless_every_scene_reports_area():
    with_area = _scene([], [_pred(0)], area_km2=10.0)
    without = _scene([], [_pred(0)])
    assert evaluate_by_size([with_area, without]).false_positives_per_100km2 is None


def test_confidence_threshold_filters_predictions_before_matching():
    scene = _scene([_vessel(0, 40)], [_pred(0, conf=0.2)])
    assert evaluate_by_size([scene], min_confidence=0.5).overall_detected == 0
    assert evaluate_by_size([scene], min_confidence=0.1).overall_detected == 1


def test_truth_without_length_counts_overall_only():
    scene = _scene([{"x_center_px": 0, "y_center_px": 0}], [_pred(0)])
    report = evaluate_by_size([scene])
    assert report.overall_truth == 1 and report.overall_detected == 1
    assert sum(b.truth for b in report.bins) == 0


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError, match="strictly increasing"):
        evaluate_by_size([], bin_edges_m=(0, 10, 10, inf))
    with pytest.raises(ValueError, match="match_radius_m"):
        evaluate_by_size([], match_radius_m=0)
    with pytest.raises(ValueError, match="pixel_size_m"):
        evaluate_by_size([_scene([], [], pixel_size_m=0)])


def test_wilson_interval_widens_for_small_samples():
    small = wilson_interval(2, 4)
    large = wilson_interval(200, 400)
    assert small is not None and large is not None
    assert (small[1] - small[0]) > (large[1] - large[0])
    assert wilson_interval(0, 0) is None
    assert wilson_interval(0, 5)[0] == 0.0


def test_comparison_marks_only_non_overlapping_changes_as_clear():
    def run(hits_small, total_small):
        truth = [_vessel(i * 100, 10) for i in range(total_small)]
        preds = [_pred(i * 100) for i in range(hits_small)]
        return evaluate_by_size([_scene(truth, preds)])

    # 1 of 4 -> 3 of 4 is a bigger change than the sample can support.
    noisy = compare_reports(run(1, 4), run(3, 4))[0]
    assert noisy["delta"] == pytest.approx(0.5) and noisy["clear"] is False
    # 20 of 200 -> 140 of 200 is a clear change.
    solid = compare_reports(run(20, 200), run(140, 200))[0]
    assert solid["clear"] is True


def test_comparison_requires_identical_bins():
    a = evaluate_by_size([], bin_edges_m=DEFAULT_BIN_EDGES_M)
    b = evaluate_by_size([], bin_edges_m=(0.0, 50.0, inf))
    with pytest.raises(ValueError, match="identical size bins"):
        compare_reports(a, b)


def test_load_xview3_truth_filters_scene_vessels_and_confidence(tmp_path):
    from evaluation.detection_by_size import load_xview3_truth

    labels = tmp_path / "labels.csv"
    labels.write_text(
        "scene_id,detect_scene_row,detect_scene_column,is_vessel,confidence,vessel_length_m\n"
        "sceneA,10,20,True,HIGH,25.5\n"
        "sceneA,11,21,True,MEDIUM,\n"
        "sceneA,12,22,True,LOW,40\n"
        "sceneA,13,23,False,HIGH,\n"
        "sceneB,14,24,True,HIGH,60\n"
        "sceneA,15,25,True,HIGH,nan\n",
        encoding="utf-8",
    )
    truth = load_xview3_truth(str(labels), "sceneA")
    assert [(t["y_center_px"], t["x_center_px"], t["length_m"]) for t in truth] == [
        (10.0, 20.0, 25.5),
        (11.0, 21.0, None),
        (15.0, 25.0, None),
    ]
    loose = load_xview3_truth(str(labels), "sceneA", allowed_confidence=("HIGH", "MEDIUM", "LOW"))
    assert len(loose) == 4
