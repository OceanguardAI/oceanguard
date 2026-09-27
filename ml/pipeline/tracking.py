"""Deterministic constant-velocity tracking baseline for coastal detections."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import hypot, isfinite
from typing import Any, Mapping


@dataclass(frozen=True)
class TrackPoint:
    track_id: str
    frame_id: str
    observed_at: datetime
    x_center_px: float
    y_center_px: float
    is_predicted: bool
    state: str
    confidence: float | None = None
    class_id: int | None = None


@dataclass
class _Track:
    track_id: str
    frame_id: str
    observed_at: datetime
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    hits: int = 1
    missed_seconds: float = 0.0
    confidence: float | None = None
    class_id: int | None = None


class BaselineTracker:
    """Greedy nearest-neighbor tracker with a short constant-velocity bridge.

    This is intentionally an interpretable baseline, not a production identity
    model. It gives later experiments a repeatable reference for HOTA, IDF1,
    identity switches, and reacquisition behavior.
    """

    def __init__(
        self,
        *,
        max_match_distance_px: float = 80.0,
        max_gap_seconds: float = 5.0,
        min_hits: int = 2,
    ) -> None:
        if (not isfinite(max_match_distance_px) or not isfinite(max_gap_seconds)
                or max_match_distance_px <= 0 or max_gap_seconds <= 0 or min_hits <= 0):
            raise ValueError("tracker limits must be positive")
        self.max_match_distance_px = max_match_distance_px
        self.max_gap_seconds = max_gap_seconds
        self.min_hits = min_hits
        self._next_id = 1
        self._tracks: dict[str, _Track] = {}
        self._last_timestamp: datetime | None = None

    def _predict(self, track: _Track, timestamp: datetime) -> tuple[float, float, float]:
        seconds = max(0.0, (timestamp - track.observed_at).total_seconds())
        return track.x + track.vx * seconds, track.y + track.vy * seconds, seconds

    def update(
        self,
        frame_id: str,
        observed_at: datetime,
        detections: list[Mapping[str, Any]],
    ) -> list[TrackPoint]:
        """Consume one frame and return matched plus short-gap predicted points."""
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("frame timestamps must include a timezone")
        if self._last_timestamp is not None and observed_at <= self._last_timestamp:
            raise ValueError("frame timestamps must be strictly increasing")
        for detection in detections:
            if not all(isfinite(float(detection[key])) for key in ("x_center_px", "y_center_px")):
                raise ValueError("detection coordinates must be finite")
        self._last_timestamp = observed_at
        predictions = {
            track_id: self._predict(track, observed_at)
            for track_id, track in self._tracks.items()
            if (observed_at - track.observed_at).total_seconds() >= 0
        }
        pairs: list[tuple[float, str, int]] = []
        for track_id, (x, y, seconds) in predictions.items():
            if seconds > self.max_gap_seconds:
                continue
            track = self._tracks[track_id]
            for index, detection in enumerate(detections):
                dx = float(detection["x_center_px"]) - x
                dy = float(detection["y_center_px"]) - y
                if "class_id" in detection and track.class_id is not None:
                    if int(detection["class_id"]) != track.class_id:
                        continue
                distance = hypot(dx, dy)
                if distance <= self.max_match_distance_px:
                    pairs.append((distance, track_id, index))

        matches: dict[str, int] = {}
        used_detections: set[int] = set()
        for _, track_id, index in sorted(pairs, key=lambda item: (item[0], item[1], item[2])):
            if track_id not in matches and index not in used_detections:
                matches[track_id] = index
                used_detections.add(index)

        points: list[TrackPoint] = []
        for track_id in sorted(self._tracks):
            track = self._tracks[track_id]
            predicted_x, predicted_y, seconds = predictions.get(track_id, (track.x, track.y, 0.0))
            if track_id in matches:
                detection = detections[matches[track_id]]
                new_x = float(detection["x_center_px"])
                new_y = float(detection["y_center_px"])
                if seconds > 0:
                    track.vx = (new_x - track.x) / seconds
                    track.vy = (new_y - track.y) / seconds
                track.x, track.y = new_x, new_y
                track.observed_at = observed_at
                track.frame_id = frame_id
                track.hits += 1
                track.missed_seconds = 0.0
                track.confidence = float(detection["confidence"]) if "confidence" in detection else track.confidence
                track.class_id = int(detection["class_id"]) if "class_id" in detection else track.class_id
                points.append(self._point(track, observed_at, False))
            elif seconds <= self.max_gap_seconds:
                track.missed_seconds = seconds
                points.append(
                    TrackPoint(
                        track_id=track_id,
                        frame_id=frame_id,
                        observed_at=observed_at,
                        x_center_px=predicted_x,
                        y_center_px=predicted_y,
                        is_predicted=True,
                        state="confirmed" if track.hits >= self.min_hits else "tentative",
                        confidence=track.confidence,
                        class_id=track.class_id,
                    )
                )
            else:
                track.missed_seconds = seconds

        for index, detection in enumerate(detections):
            if index in used_detections:
                continue
            track_id = f"track-{self._next_id:06d}"
            self._next_id += 1
            track = _Track(
                track_id=track_id,
                frame_id=frame_id,
                observed_at=observed_at,
                x=float(detection["x_center_px"]),
                y=float(detection["y_center_px"]),
                confidence=float(detection["confidence"]) if "confidence" in detection else None,
                class_id=int(detection["class_id"]) if "class_id" in detection else None,
            )
            self._tracks[track_id] = track
            points.append(self._point(track, observed_at, False))

        expired = [track_id for track_id, track in self._tracks.items() if track.missed_seconds > self.max_gap_seconds]
        for track_id in expired:
            del self._tracks[track_id]
        return sorted(points, key=lambda point: point.track_id)

    def _point(self, track: _Track, timestamp: datetime, predicted: bool) -> TrackPoint:
        return TrackPoint(
            track_id=track.track_id,
            frame_id=track.frame_id,
            observed_at=timestamp,
            x_center_px=track.x,
            y_center_px=track.y,
            is_predicted=predicted,
            state="confirmed" if track.hits >= self.min_hits else "tentative",
            confidence=track.confidence,
            class_id=track.class_id,
        )
