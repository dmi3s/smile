from dataclasses import dataclass

from smile.recognition.detectors.face_detection import DetectedFaceBox, FaceBox

DEFAULT_ALPHA = 0.4
DEFAULT_MAX_DIST = 0.3
DEFAULT_MAX_LOST = 2


@dataclass(slots=True)
class FaceTrack:
    face_id: int
    bbox: FaceBox
    score: float
    last_raw: FaceBox
    lost_frames: int


def _ema(prev: float, value: float, alpha: float) -> float:
    return prev * (1.0 - alpha) + value * alpha


class FaceTracker:
    """Tracks detected faces across frames and smooths their boxes.

    Pure logic, no Qt. Coordinates are normalized [0, 1].

    Matching is greedy nearest-center with a distance threshold: each new box
    claims the closest still-free track within `max_dist`. Tracks without a
    match survive for up to `max_lost` frames (handles detection dropouts)
    and are then pruned. When a brand-new track appears while an old track is
    being held, the held track is dropped immediately — the old face is
    considered gone.
    """

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        max_dist: float = DEFAULT_MAX_DIST,
        max_lost: int = DEFAULT_MAX_LOST,
    ) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        if max_dist <= 0.0:
            raise ValueError("max_dist must be positive")
        if max_lost < 0:
            raise ValueError("max_lost must be non-negative")

        self._alpha = alpha
        self._max_dist = max_dist
        self._max_lost = max_lost
        self._tracks: list[FaceTrack] = []
        self._next_id = 0

    def _center(self, bbox: FaceBox) -> tuple[float, float]:
        return (bbox.fx + bbox.fw / 2.0, bbox.fy + bbox.fh / 2.0)

    def _distance(self, a: FaceBox, b: FaceBox) -> float:
        ax, ay = self._center(a)
        bx, by = self._center(b)
        return max(abs(ax - bx), abs(ay - by))

    def update(self, faces: tuple[DetectedFaceBox, ...]) -> tuple[DetectedFaceBox, ...]:
        remaining = list(self._tracks)
        matched: list[tuple[FaceTrack, DetectedFaceBox]] = []
        unmatched_detections: list[DetectedFaceBox] = []

        for detected in faces:
            best: tuple[FaceTrack, float] | None = None
            best_index = -1
            for index, track in enumerate(remaining):
                if track.lost_frames > 0:
                    continue
                dist = self._distance(track.last_raw, detected.bbox)
                if dist > self._max_dist:
                    continue
                if best is None or dist < best[1]:
                    best = (track, dist)
                    best_index = index

            if best is not None and best_index >= 0:
                matched.append((best[0], detected))
                remaining.pop(best_index)
            else:
                unmatched_detections.append(detected)

        new_tracks: list[FaceTrack] = []
        for track in remaining:
            track.lost_frames += 1
            if track.lost_frames <= self._max_lost:
                new_tracks.append(track)

        for track, detected in matched:
            raw = detected.bbox
            track.bbox = FaceBox(
                fx=_ema(track.bbox.fx, raw.fx, self._alpha),
                fy=_ema(track.bbox.fy, raw.fy, self._alpha),
                fw=_ema(track.bbox.fw, raw.fw, self._alpha),
                fh=_ema(track.bbox.fh, raw.fh, self._alpha),
            )
            track.score = _ema(track.score, detected.score, self._alpha)
            track.last_raw = raw
            track.lost_frames = 0
            new_tracks.append(track)

        if unmatched_detections:
            new_tracks = [track for track in new_tracks if track.lost_frames == 0]

        for detected in unmatched_detections:
            new_tracks.append(
                FaceTrack(
                    face_id=self._next_id,
                    bbox=detected.bbox,
                    score=detected.score,
                    last_raw=detected.bbox,
                    lost_frames=0,
                )
            )
            self._next_id += 1

        self._tracks = new_tracks

        return tuple(
            DetectedFaceBox(bbox=track.bbox, score=track.score)
            for track in self._tracks
        )

    def reset(self) -> None:
        self._tracks = []
        self._next_id = 0
