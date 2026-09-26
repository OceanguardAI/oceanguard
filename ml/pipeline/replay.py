"""Replay recorded frame detections through the baseline tracker."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from pipeline.tracking import BaselineTracker


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("frame timestamps must include a timezone")
    return parsed


def replay_sequence(
    frames: Iterable[Mapping[str, Any]],
    *,
    max_match_distance_px: float = 80.0,
    max_gap_seconds: float = 5.0,
) -> list[dict[str, Any]]:
    """Replay frames in input order and return JSON-ready track points."""
    tracker = BaselineTracker(
        max_match_distance_px=max_match_distance_px,
        max_gap_seconds=max_gap_seconds,
    )
    points: list[dict[str, Any]] = []
    previous_timestamp: datetime | None = None
    for frame in frames:
        timestamp = _timestamp(str(frame["observed_at"]))
        if previous_timestamp and timestamp < previous_timestamp:
            raise ValueError("frames must be ordered by observed_at")
        previous_timestamp = timestamp
        frame_id = str(frame["frame_id"])
        detections = frame.get("detections", [])
        if not isinstance(detections, list):
            raise ValueError("frame detections must be a list")
        for point in tracker.update(frame_id, timestamp, detections):
            payload = asdict(point)
            payload["observed_at"] = point.observed_at.isoformat()
            points.append(payload)
    return points


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay detections through the baseline tracker")
    parser.add_argument("--input", type=Path, required=True, help="JSON list of frame records")
    parser.add_argument("--output", type=Path, required=True, help="JSON track-point output")
    parser.add_argument("--max-match-distance-px", type=float, default=80.0)
    parser.add_argument("--max-gap-seconds", type=float, default=5.0)
    args = parser.parse_args()
    frames = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(frames, list):
        raise ValueError("input JSON must be a list of frames")
    points = replay_sequence(
        frames,
        max_match_distance_px=args.max_match_distance_px,
        max_gap_seconds=args.max_gap_seconds,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(points, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {len(points)} track points to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
