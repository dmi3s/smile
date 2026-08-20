from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np

from smile.recognition.detectors.face_detection import FaceBox

# ImageNet label keywords that mean "flashlight" in the classifier output.
# In mobilenet_v2_1.0_224.tflite the "torch" class has index 863.
FLASHLIGHT_KEYWORDS = ("torch", "flashlight", "hand torch")
FLASHLIGHT_SCORE_MIN = 0.03

# Bright-spot (glowing lens) heuristic thresholds.
BRIGHT_THRESHOLD = 200  # 0..255, blown-out pixels
MIN_AREA_RATIO = 0.005  # at least 0.5% of the frame
MAX_AREA_RATIO = 0.6  # more than that and the whole scene is flooded


@dataclass(slots=True, frozen=True)
class Category:
    index: int
    score: float
    name: str


@dataclass(slots=True, frozen=True)
class BrightSpot:
    bbox: FaceBox
    area_ratio: float
    peak: float


@dataclass(slots=True, frozen=True)
class FlashlightDetectionResult:
    detected: bool
    score: float
    bright_bbox: FaceBox | None
    brightness: float
    frame_id: int


def is_flashlight(
    categories: Sequence[Category], score_min: float = FLASHLIGHT_SCORE_MIN
) -> tuple[bool, float]:
    """Return (detected, best_score) from the top classifier categories."""
    for category in categories:
        if category.score < score_min:
            break
        name = category.name.lower()
        if any(keyword in name for keyword in FLASHLIGHT_KEYWORDS):
            return True, category.score
    return False, 0.0


def hybrid_flashlight_result(
    classifier_detected: bool,
    classifier_score: float,
    spot: BrightSpot | None,
    frame_id: int,
) -> FlashlightDetectionResult:
    """Combine the ImageNet classifier and the bright-spot heuristic.

    The device counts when either the classifier sees a torch (works even
    with the light off) or a bright lens is actually glowing. The score
    comes from the classifier when it fired, otherwise from the lens
    brightness.
    """
    detected = classifier_detected or spot is not None
    score = (
        classifier_score
        if classifier_detected
        else (spot.peak if spot is not None else 0.0)
    )
    return FlashlightDetectionResult(
        detected=detected,
        score=score,
        bright_bbox=spot.bbox if spot is not None else None,
        brightness=spot.peak if spot is not None else 0.0,
        frame_id=frame_id,
    )


def detect_bright_spot(
    image: np.ndarray,
    threshold: int = BRIGHT_THRESHOLD,
    min_area_ratio: float = MIN_AREA_RATIO,
    max_area_ratio: float = MAX_AREA_RATIO,
) -> BrightSpot | None:
    """Find the largest blown-out region in the image.

    Coordinates are normalized [0, 1] relative to the image, so the caller
    can map them onto the full-resolution frame.
    """
    gray = image.mean(axis=2)
    height, width = gray.shape
    if width == 0 or height == 0:
        return None

    mask = (gray > threshold).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    components, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask, connectivity=8
    )
    if components <= 1:
        return None

    best: tuple[int, float, FaceBox, float] | None = None
    for i in range(1, components):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area == 0:
            continue
        ratio = area / (width * height)
        if ratio < min_area_ratio or ratio > max_area_ratio:
            continue
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        peak = float(gray[labels == i].max()) / 255.0
        if best is None or area > best[0]:
            best = (
                area,
                ratio,
                FaceBox(
                    fx=x / width,
                    fy=y / height,
                    fw=w / width,
                    fh=h / height,
                ),
                peak,
            )

    if best is None:
        return None

    return BrightSpot(bbox=best[2], area_ratio=best[1], peak=best[3])
