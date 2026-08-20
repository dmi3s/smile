import numpy as np

from smile.recognition.detectors.face_detection import FaceBox
from smile.recognition.detectors.flashlight_detection import (
    BrightSpot,
    Category,
    detect_bright_spot,
    hybrid_flashlight_result,
    is_flashlight,
)


def _dark_image():
    return np.zeros((448, 800, 3), dtype=np.uint8)


def test_no_bright_spot_on_dark_image():
    assert detect_bright_spot(_dark_image()) is None


def test_bright_spot_detected():
    img = _dark_image()
    img[100:150, 300:500] = 255
    spot = detect_bright_spot(img)
    assert spot is not None
    assert spot.bbox.fx == 300 / 800
    assert spot.bbox.fy == 100 / 448
    assert spot.bbox.fw == 200 / 800
    assert spot.bbox.fh == 50 / 448
    assert spot.peak == 1.0


def test_bright_spot_too_small_ignored():
    img = _dark_image()
    img[223, 400] = 255
    assert detect_bright_spot(img) is None


def test_bright_spot_flooded_frame_ignored():
    img = np.full((448, 800, 3), 255, dtype=np.uint8)
    assert detect_bright_spot(img) is None


def test_largest_spot_wins():
    img = _dark_image()
    img[50:100, 50:150] = 255
    img[200:400, 500:800] = 255
    spot = detect_bright_spot(img)
    assert spot is not None
    assert spot.bbox.fy == 200 / 448
    assert spot.bbox.fx == 500 / 800


def test_is_flashlight_matches_torch():
    cats = (
        Category(0, 0.9, "television"),
        Category(1, 0.8, "torch"),
        Category(2, 0.1, "matchstick"),
    )
    assert is_flashlight(cats) == (True, 0.8)


def test_is_flashlight_case_insensitive():
    cats = (Category(0, 0.7, "Flashlight"),)
    assert is_flashlight(cats) == (True, 0.7)


def test_is_flashlight_no_match():
    cats = (Category(0, 0.9, "picket fence"), Category(1, 0.8, "obelisk"))
    assert is_flashlight(cats) == (False, 0.0)


def test_is_flashlight_below_score_threshold():
    cats = (Category(0, 0.02, "torch"),)
    assert is_flashlight(cats) == (False, 0.0)


def test_is_flashlight_empty():
    assert is_flashlight(()) == (False, 0.0)


def test_hybrid_detected_by_classifier_without_spot():
    result = hybrid_flashlight_result(True, 0.8, None, frame_id=1)
    assert result.detected is True
    assert result.score == 0.8
    assert result.bright_bbox is None


def test_hybrid_detected_by_bright_spot_only():
    spot = BrightSpot(bbox=FaceBox(0.3, 0.4, 0.2, 0.3), area_ratio=0.05, peak=0.9)
    result = hybrid_flashlight_result(False, 0.0, spot, frame_id=2)
    assert result.detected is True
    assert result.score == 0.9
    assert result.bright_bbox == spot.bbox
    assert result.brightness == 0.9


def test_hybrid_not_detected_when_nothing_found():
    result = hybrid_flashlight_result(False, 0.0, None, frame_id=3)
    assert result.detected is False
    assert result.score == 0.0
    assert result.bright_bbox is None
