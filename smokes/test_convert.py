from PySide6.QtCore import QRect
from PySide6.QtGui import QColor

from smile.recognition.detectors.face_detection import DetectedFaceBox, FaceBox
from smile.utils.convert import face_to_qrect, face_to_qrect_with_color


def _box(
    fx: float = 0.1,
    fy: float = 0.2,
    fw: float = 0.3,
    fh: float = 0.4,
    score: float = 0.5,
) -> DetectedFaceBox:
    return DetectedFaceBox(bbox=FaceBox(fx, fy, fw, fh), score=score)


def test_face_to_qrect_scales():
    rect = face_to_qrect(_box(), 800, 448)
    assert rect == QRect(80, 89, 240, 179)


def test_face_to_qrect_clamps_to_bounds():
    rect = face_to_qrect(_box(fx=0.9, fy=0.9, fw=0.5, fh=0.5), 100, 100)
    assert rect.right() <= 99
    assert rect.bottom() <= 99


def test_face_to_qrect_with_color_red_at_low_score():
    rect, color = face_to_qrect_with_color(_box(score=0.0), 800, 448)
    assert isinstance(rect, QRect)
    assert isinstance(color, QColor)
    assert color.red() >= color.green()


def test_face_to_qrect_with_color_green_at_high_score():
    rect, color = face_to_qrect_with_color(_box(score=1.0), 800, 448)
    assert isinstance(rect, QRect)
    assert color.green() > color.red()
