import numpy as np
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QLabel

from smile.recognition.detectors.face_detection import DetectedFaceBox
from smile.utils.convert import face_to_qrect_with_color
from smile.utils.smooth import FloatSmoother


class OverlayLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._image: QImage | None = None
        self._image_ref: np.ndarray | None = None
        self._face_boxes: tuple[DetectedFaceBox, ...] = ()

        self._show_statistics: bool = False
        self._fps_smooth = FloatSmoother(alpha=0.03)
        self._prev_timestamp_ns: int = 0
        self._timestamp_ns: int = 0

    def set_frame(
        self,
        image: np.ndarray,
        face_boxes: tuple[DetectedFaceBox, ...],
        time_ns: int,
        show_statistics=False,
    ) -> None:
        """Thread-safe update: call from GUI thread only."""
        height, width, channels = image.shape
        self._image_ref = image
        self._image = QImage(
            image.data, width, height, channels * width, QImage.Format.Format_BGR888
        )
        self._face_boxes = face_boxes
        self._timestamp_ns = time_ns
        self._show_statistics = show_statistics
        self.update()

    def _draw_rect(self) -> QRect:
        if self._image is None:
            return QRect()
        image_w, image_h = self._image.width(), self._image.height()
        widget_w, widget_h = self.width(), self.height()
        if widget_w <= 0 or widget_h <= 0:
            return QRect()
        scale = min(widget_w / image_w, widget_h / image_h)
        draw_w = max(1, round(image_w * scale))
        draw_h = max(1, round(image_h * scale))
        x = (widget_w - draw_w) // 2
        y = (widget_h - draw_h) // 2
        return QRect(x, y, draw_w, draw_h)

    def _map_rect(self, rect: QRect) -> QRect:
        draw_rect = self._draw_rect()
        if self._image is None or draw_rect.isEmpty():
            return QRect()
        sx = draw_rect.width() / self._image.width()
        sy = draw_rect.height() / self._image.height()
        return QRect(
            draw_rect.x() + round(rect.x() * sx),
            draw_rect.y() + round(rect.y() * sy),
            max(1, round(rect.width() * sx)),
            max(1, round(rect.height() * sy)),
        )

    def paintEvent(self, event):
        super().paintEvent(event)

        with QPainter(self) as p:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)

            if self._image is not None:
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                p.drawImage(self._draw_rect(), self._image)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)

                for fb in self._face_boxes:
                    rect, color = face_to_qrect_with_color(
                        fb, self._image.width(), self._image.height()
                    )
                    pen = QPen(color, 2)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                    p.setPen(pen)
                    p.drawRect(self._map_rect(rect))

            if self._show_statistics and self._timestamp_ns > 0:
                delta = self._timestamp_ns - self._prev_timestamp_ns
                if delta > 0:
                    fps: float = self._fps_smooth.update(1e9 / delta)
                    self._prev_timestamp_ns = self._timestamp_ns

                    pen = QPen(QColor("lime"), 2)
                    p.setPen(pen)
                    p.drawText(10, 10, f"FPS: {fps:.1f}")
