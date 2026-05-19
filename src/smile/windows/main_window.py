import logging

from PySide6.QtCore import QRect, Slot
from PySide6.QtGui import QBrush, QImage, QPainter, QPen, QPixmap, Qt
from PySide6.QtWidgets import QMainWindow

from smile.camera import frame
from smile.camera.frame import Frame
from smile.recognition.face_detection import RecognitionResult
from smile.ui.generated.ui_main_window import Ui_MainWindow

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._recognition_result = RecognitionResult([], 0, 0)
        self._prev_time_ns = 0

    @Slot(Frame)
    def update_frame(self, frame: Frame) -> None:
        image = frame.image
        height, width, channels = image.shape
        # logger.info(f"Frame {frame.frame_id} {width} x {height} x {channels}")
        bytes_per_line = channels * width

        qimage = QImage(
            image.copy().data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        ).copy()

        pixmap = QPixmap.fromImage(qimage)

        if self._recognition_result.faces:
            painter = QPainter(pixmap)
            try:
                pen = QPen(Qt.GlobalColor.green)
                pen.setWidth(2)
                painter.setPen(pen)
                for face in self._recognition_result.faces:
                    rect = QRect(
                        int( face.bbox.fx * pixmap.width() ),
                        int( face.bbox.fy * pixmap.height() ),
                        int( face.bbox.fw * pixmap.width() ),
                        int( face.bbox.fh * pixmap.height() ),
                    )
                    painter.drawRect(rect)
            finally:
                painter.end()

        self.ui.video_label.setPixmap(pixmap)
        fps: float = 1_000_000_000 / (frame.timestamp_ns - self._prev_time_ns)
        self._prev_time_ns = frame.timestamp_ns
        self.ui.statusbar.showMessage(f"fps: {fps:.2f}")

    @Slot(RecognitionResult)
    def update_detection(self, detection_result: RecognitionResult) -> None:
        self._recognition_result = detection_result
        if len(detection_result.faces):
            self.ui.smile_label.setText("😐")
        else:
            self.ui.smile_label.setText("🖖") # ("👾")

