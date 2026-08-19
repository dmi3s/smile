import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class Point(Protocol):
    x: float
    y: float


# MediaPipe FaceMesh landmark indices (478-point topology).
# References:
#   https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/face_mesh.md
UPPER_LIP_CENTER = 13  # center of the top outer lip
LOWER_LIP_CENTER = 14  # center of the bottom outer lip
LEFT_MOUTH_CORNER = 61
RIGHT_MOUTH_CORNER = 291
LEFT_EYE_OUTER = 33
RIGHT_EYE_OUTER = 263

# Smile scoring thresholds, calibrated on real camera data:
#   neutral mouth: openness ~0.005, spread ~0.55-0.65
#   open-mouth smile: openness 0.25-0.30+
#   closed-lip smile: spread 0.72-0.78
# Both metrics fall back below the thresholds on a neutral face, so the
# score self-resets and the smile indicator disappears.
OPEN_MIN = 0.12
OPEN_MAX = 0.30
SPREAD_MIN = 0.72
SPREAD_MAX = 0.85

# Corner lift above the lip line, calibrated on real camera data:
#   neutral: 0.08-0.20, bared-teeth grimace (open mouth, corners down): 0.09-0.15,
#   genuine smile: 0.20-0.29.
# The openness term is gated by this lift so that an open mouth without
# raised corners (grimace, yawn, talking) does not score as a smile.
LIFT_MIN = 0.18
LIFT_MAX = 0.28


@dataclass(slots=True, frozen=True)
class SmileFeatures:
    openness: float
    spread: float
    corner_rise: float
    corner_lift: float


@dataclass(slots=True, frozen=True)
class SmileDetectionResult:
    smile_scores: tuple[float, ...]  # one score per detected face, 0.0..1.0
    frame_id: int


def mouth_features(landmarks: Sequence[Point]) -> SmileFeatures | None:
    """Extract smile-relevant mouth geometry or None if it is degenerate."""
    left = landmarks[LEFT_MOUTH_CORNER]
    right = landmarks[RIGHT_MOUTH_CORNER]
    upper = landmarks[UPPER_LIP_CENTER]
    lower = landmarks[LOWER_LIP_CENTER]
    left_eye = landmarks[LEFT_EYE_OUTER]
    right_eye = landmarks[RIGHT_EYE_OUTER]

    width = math.dist((left.x, left.y), (right.x, right.y))
    eye_width = math.dist((left_eye.x, left_eye.y), (right_eye.x, right_eye.y))
    if width <= 0.0 or eye_width <= 0.0:
        return None

    height = math.dist((upper.x, upper.y), (lower.x, lower.y))
    openness = height / width

    spread = width / eye_width

    eye_y = (left_eye.y + right_eye.y) / 2.0
    corners_y = (left.y + right.y) / 2.0
    corner_rise = (eye_y - corners_y) / eye_width  # grows as corners pull up

    lips_y = (upper.y + lower.y) / 2.0
    corner_lift = (lips_y - corners_y) / width  # >0 when corners above lip line

    return SmileFeatures(
        openness=openness,
        spread=spread,
        corner_rise=corner_rise,
        corner_lift=corner_lift,
    )


def smile_score(landmarks: Sequence[Point]) -> float:
    """Continuous smile score in [0, 1] for a single face."""
    features = mouth_features(landmarks)
    if features is None:
        return 0.0

    open_score = _clamp01((features.openness - OPEN_MIN) / (OPEN_MAX - OPEN_MIN))
    spread_score = _clamp01((features.spread - SPREAD_MIN) / (SPREAD_MAX - SPREAD_MIN))
    lift_gate = _clamp01((features.corner_lift - LIFT_MIN) / (LIFT_MAX - LIFT_MIN))
    return max(spread_score, open_score * lift_gate)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
