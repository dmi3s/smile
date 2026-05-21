from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel

from smile.utils.convert import ColoredQRect
from smile.utils.lerp import lerp
from smile.utils.smooth import FloatSmoother


class OverlayLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._detection_rects: tuple[ColoredQRect, ...] = ()

        self._show_statistics: bool = False
        self._fps_smooth = FloatSmoother(alpha= 0.05)
        self._prev_timestamp_ns: int = 0
        self._timestamp_ns: int = 0

    def set_detections(self, rects: tuple[ColoredQRect, ...], time_ns: int, show_statistics = False) -> None:
        """Thread-safe update: call from GUI thread only"""
        self._detection_rects = rects
        self._timestamp_ns = time_ns
        self._show_statistics = show_statistics
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        with QPainter(self) as p:
            if self._detection_rects is not None:
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                pen = QPen(QColor("lime"), 2)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)  # Сглаживает углы рамок
                p.setPen(pen)

                for r, color in self._detection_rects:
                    pen = QPen(color, 2)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                    p.setPen(pen)
                    p.drawRect(r)

            if self._show_statistics and self._timestamp_ns > 0:
                delta = self._timestamp_ns - self._prev_timestamp_ns
                if delta > 0:
                    fps: float = self._fps_smooth.update(1e9 / delta)
                    self._prev_timestamp_ns = self._timestamp_ns
                    
                    pen = QPen(QColor("lime"), 2)
                    p.setPen(pen)
                    p.drawText(10, 10, f"FPS: {fps:.1f}")

