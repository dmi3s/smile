from PySide6.QtCore import QRect
from PySide6.QtGui import QColor

from smile.recognition.detectors.face_detection import DetectedFaceBox
from smile.utils.lerp import lerp

ColoredQRect = tuple[QRect, QColor]


def face_to_qrect(
    fb: DetectedFaceBox, width: float | int, height: float | int
) -> QRect:
    rect = QRect(
        int(fb.bbox.fx * width),
        int(fb.bbox.fy * height),
        int(fb.bbox.fw * width),
        int(fb.bbox.fh * height),
    )
    # Clamp to widget bounds
    rect = rect.intersected(QRect(0, 0, int(width), int(height)))
    return rect


def face_to_qrect_with_color(
    fb: DetectedFaceBox, width: float | int, height: float | int
) -> ColoredQRect:
    # Color gradient: red (0.0) → yellow (0.5) → green (1.0)
    alpha = 3.0 * (fb.score - 0.75)
    r = int(lerp(0, 255, max(0.0, 1.0 - alpha)))
    g = int(lerp(0, 255, min(1.0, alpha)))
    color = QColor(r, g, 84)
    return face_to_qrect(fb, width, height), color


def faces_to_qrects(
    face_boxes: tuple[DetectedFaceBox, ...], width: float | int, height: float | int
) -> tuple[QRect, ...]:
    return tuple(face_to_qrect(fb, width, height) for fb in face_boxes)


def faces_to_qrects_with_colors(
    face_boxes: tuple[DetectedFaceBox, ...], width: float | int, height: float | int
) -> tuple[ColoredQRect, ...]:
    return tuple(face_to_qrect_with_color(fb, width, height) for fb in face_boxes)
