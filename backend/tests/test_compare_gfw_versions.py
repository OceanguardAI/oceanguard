from __future__ import annotations

import pytest

from app.tools.compare_gfw_versions import compare_activity


def _row(lat: float, lon: float, n: int) -> dict:
    return {"lat": lat, "lon": lon, "detections": n}


def test_identical_versions_agree_perfectly() -> None:
    rows = [_row(8.5, 79.6, 3), _row(8.6, 79.7, 1), _row(8.7, 79.8, 5)]
    result = compare_activity(rows, list(rows))
    assert result["cells"]["jaccard"] == 1.0
    assert result["detections"]["ratio_b_over_a"] == 1.0
    assert result["shared_cells"]["mean_abs_count_difference"] == 0
    assert result["shared_cells"]["pearson_r"] == pytest.approx(1.0)
    assert result["top_50_cell_overlap"] == 1.0


def test_disjoint_and_partial_overlap_are_reported_separately() -> None:
    a = [_row(1, 1, 2), _row(2, 2, 2)]
    b = [_row(2, 2, 4), _row(3, 3, 1)]
    cells = compare_activity(a, b)["cells"]
    assert (cells["shared"], cells["only_a"], cells["only_b"]) == (1, 1, 1)
    assert cells["jaccard"] == pytest.approx(1 / 3)


def test_totals_ratio_and_count_difference() -> None:
    result = compare_activity([_row(1, 1, 10), _row(2, 2, 10)], [_row(1, 1, 5), _row(2, 2, 5)])
    assert result["detections"] == {"a": 20, "b": 10, "ratio_b_over_a": 0.5}
    assert result["shared_cells"]["mean_abs_count_difference"] == 5


def test_duplicate_rows_for_one_cell_are_summed() -> None:
    result = compare_activity([_row(1, 1, 2), _row(1, 1, 3)], [_row(1, 1, 5)])
    assert result["cells"]["shared"] == 1
    assert result["shared_cells"]["mean_abs_count_difference"] == 0


def test_empty_inputs_do_not_divide_by_zero() -> None:
    result = compare_activity([], [])
    assert result["cells"]["jaccard"] is None
    assert result["detections"]["ratio_b_over_a"] is None
    assert result["shared_cells"]["pearson_r"] is None
    assert result["top_50_cell_overlap"] is None


def test_constant_counts_give_undefined_correlation_not_an_error() -> None:
    rows = [_row(1, 1, 2), _row(2, 2, 2)]
    assert compare_activity(rows, rows)["shared_cells"]["pearson_r"] is None


def test_malformed_rows_are_skipped() -> None:
    result = compare_activity([{"lat": "x", "lon": 1}, {"lon": 1}, _row(1, 1, 2)], [_row(1, 1, 2)])
    assert result["cells"]["a"] == 1


def test_context_totals_use_the_classifier() -> None:
    def classify(lat: float, lon: float) -> str:
        return "inside_mpa" if lat < 5 else "open_water"

    result = compare_activity(
        [_row(1, 1, 4), _row(9, 9, 6)], [_row(1, 1, 2), _row(9, 9, 6)], classify=classify)
    assert result["by_context"] == {
        "inside_mpa": {"a": 4, "b": 2},
        "open_water": {"a": 6, "b": 6},
    }


def test_top_cell_overlap_measures_ranking_stability() -> None:
    a = [_row(1, 1, 9), _row(2, 2, 8), _row(3, 3, 1)]
    b = [_row(1, 1, 9), _row(3, 3, 8), _row(2, 2, 1)]
    assert compare_activity(a, b, top_n=2)["top_2_cell_overlap"] == pytest.approx(0.5)
