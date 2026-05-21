import logging

from PySide6.QtCore import Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QMainWindow, QMessageBox

from smile.camera.frame import Frame
from smile.recognition.detectors.face_detection import RecognitionResult
from smile.ui.generated.ui_main_window import Ui_MainWindow
from smile.utils.convert import ColoredQRect, faces_to_qrects_with_colors

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._recognition_result = RecognitionResult(tuple(), frame_rgb = None)


    @Slot(Frame)
    def update_frame(self, frame: Frame) -> None:
        if not self.isVisible():
            return

        image = frame.image
        height, width, channels = image.shape
        # logger.info(f"Frame {frame.frame_id} {width} x {height} x {channels}")
        bytes_per_line = channels * width

        qimage = QImage(
            image.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        ).copy()

        pixmap = QPixmap.fromImage(qimage)
        self.ui.video_label.setPixmap(pixmap)

        coords : tuple[ColoredQRect, ...] = faces_to_qrects_with_colors(
            self._recognition_result.faces,
            pixmap.width(),
            pixmap.height()
        )

        ts_ns =  frame.timestamp_ns if frame else 0
        self.ui.video_label.set_detections(
            coords,
            ts_ns,
            True
        )


    @Slot(RecognitionResult)
    def update_face_recognition(self, detection_result: RecognitionResult) -> None:
        self._recognition_result = detection_result
        if len(detection_result.faces):
            self.ui.smile_label.setText("😐")
        else:
            self.ui.smile_label.setText("🖖") # ("👾")

    @Slot(RecognitionResult)
    def update_smile_status(self, smile_status: RecognitionResult) -> None:
        logger.info(f"update_smile_status: {smile_status=}")

    @Slot(str)
    def camera_worker_error(self, msg: str) -> None:
        QMessageBox.critical(
            self,
            "Camera Error",
            f"{msg}\n\nPlease check camera connection and restart."
        )