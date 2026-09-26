"""Dependency-light tracking metrics for baseline experiments.

The evaluator is deliberately explicit about its matching threshold and input
contract. It is useful for regression tests and quick experiments; final paper
results should be cross-checked with the official benchmark implementations.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from math import hypot
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class TrackingMetrics:
    detection_precision: float
    detection_recall: float
    idtp: int
    idfp: int
    idfn: int
    idf1: float
    identity_switches: int
    fragmentation: int
    matched_pairs: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _match_frame(
    truth: list[Mapping[str, Any]],
    predictions: list[Mapping[str, Any]],
    max_distance_px: float,
) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    pairs: list[tuple[float, int, int]] = []
    for truth_index, expected in enumerate(truth):
        for prediction_index, actual in enumerate(predictions):
            distance = hypot(
                float(expected["x_center_px"]) - float(actual["x_center_px"]),
                float(expected["y_center_px"]) - float(actual["y_center_px"]),
            )
            if distance <= max_distance_px:
                pairs.append((distance, truth_index, prediction_index))
    matched_truth: set[int] = set()
    matched_predictions: set[int] = set()
    matches: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    for _, truth_index, prediction_index in sorted(pairs, key=lambda item: item):
        if truth_index in matched_truth or prediction_index in matched_predictions:
            continue
        matched_truth.add(truth_index)
        matched_predictions.add(prediction_index)
        matches.append((truth[truth_index], predictions[prediction_index]))
    return matches


def _maximum_assignment(pair_counts: Counter[tuple[str, str]]) -> int:
    """Return a maximum one-to-one identity assignment score.

    A small dynamic-programming assignment is enough for evaluation fixtures and
    avoids making SciPy a required runtime dependency. For very large identity
    sets, a caller should use an official benchmark implementation instead.
    """
    truth_ids = sorted({truth_id for truth_id, _ in pair_counts})
    prediction_ids = sorted({prediction_id for _, prediction_id in pair_counts})
    if len(prediction_ids) > 20:
        # A deterministic greedy fallback keeps the helper usable on large runs.
        used: set[str] = set()
        return sum(
            count
            for truth_id in truth_ids
            for prediction_id, count in sorted(
                ((candidate, pair_counts[(truth_id, candidate)]) for candidate in prediction_ids if candidate not in used),
                key=lambda item: (-item[1], item[0]),
            )[:1]
            if not used.add(prediction_id)
        )

    scores: dict[tuple[int, int], int] = {}

    def solve(truth_index: int, used_mask: int) -> int:
        key = (truth_index, used_mask)
        if key in scores:
            return scores[key]
        if truth_index == len(truth_ids):
            return 0
        best = solve(truth_index + 1, used_mask)
        truth_id = truth_ids[truth_index]
        for prediction_index, prediction_id in enumerate(prediction_ids):
            if used_mask & (1 << prediction_index):
                continue
            best = max(
                best,
                pair_counts[(truth_id, prediction_id)]
                + solve(truth_index + 1, used_mask | (1 << prediction_index)),
            )
        scores[key] = best
        return best

    return solve(0, 0)


def evaluate_tracking(
    ground_truth: Iterable[Mapping[str, Any]],
    predictions: Iterable[Mapping[str, Any]],
    *,
    max_distance_px: float = 50.0,
) -> TrackingMetrics:
    """Evaluate frame detections and identity continuity.

    Required truth keys are ``frame_id``, ``gt_id``, ``x_center_px``, and
    ``y_center_px``. Predictions use ``track_id`` in place of ``gt_id``.
    """
    if max_distance_px <= 0:
        raise ValueError("max_distance_px must be positive")
    truth_by_frame: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    predictions_by_frame: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in ground_truth:
        truth_by_frame[str(item["frame_id"])].append(item)
    for item in predictions:
        predictions_by_frame[str(item["frame_id"])].append(item)

    pair_counts: Counter[tuple[str, str]] = Counter()
    matched_by_truth: dict[str, list[tuple[str, str]]] = defaultdict(list)
    matched_pairs = 0
    for frame_id in sorted(set(truth_by_frame) | set(predictions_by_frame)):
        matches = _match_frame(truth_by_frame[frame_id], predictions_by_frame[frame_id], max_distance_px)
        matched_pairs += len(matches)
        for expected, actual in matches:
            truth_id = str(expected["gt_id"])
            prediction_id = str(actual["track_id"])
            pair_counts[(truth_id, prediction_id)] += 1
            matched_by_truth[truth_id].append((frame_id, prediction_id))

    truth_count = sum(len(items) for items in truth_by_frame.values())
    prediction_count = sum(len(items) for items in predictions_by_frame.values())
    idtp = _maximum_assignment(pair_counts)
    idfp = prediction_count - idtp
    idfn = truth_count - idtp
    identity_switches = 0
    fragmentation = 0
    for matches in matched_by_truth.values():
        ordered = [prediction_id for _, prediction_id in sorted(matches)]
        identity_switches += sum(previous != current for previous, current in zip(ordered, ordered[1:]))
        frame_indexes = [int(frame_id) for frame_id, _ in matches if frame_id.isdigit()]
        fragmentation += sum(b > a + 1 for a, b in zip(sorted(frame_indexes), sorted(frame_indexes)[1:]))

    precision = matched_pairs / prediction_count if prediction_count else 0.0
    recall = matched_pairs / truth_count if truth_count else 0.0
    idf1 = (2 * idtp) / (2 * idtp + idfp + idfn) if (2 * idtp + idfp + idfn) else 0.0
    return TrackingMetrics(
        detection_precision=precision,
        detection_recall=recall,
        idtp=idtp,
        idfp=idfp,
        idfn=idfn,
        idf1=idf1,
        identity_switches=identity_switches,
        fragmentation=fragmentation,
        matched_pairs=matched_pairs,
    )
