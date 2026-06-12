import logging
from types import TracebackType
from typing import override

from PySide6.QtCore import QEvent, QObject, QSize, Qt, Slot
from PySide6.QtGui import QImage, QKeyEvent, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

from smile.camera.frame import Frame
from smile.recognition.detectors.face_detection import FaceDetectionResult
from smile.recognition.detectors.smile_detection import SmileDetectionResult
from smile.ui.generated.ui_main_window import Ui_MainWindow
from smile.utils.convert import ColoredQRect, faces_to_qrects_with_colors

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._face_detection_result = FaceDetectionResult(
            tuple(),
            small_frame_rgb=None,
        )
        self.installEventFilter(self)
        self._camera_frame_id = 0

    @override
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key_event = QKeyEvent(event)
            logger.info(f"KeyPress: {key_event.key()} with modifiers= {key_event.modifiers()}")
            if (
                key_event.key() == Qt.Key.Key_Q
                and key_event.modifiers() == Qt.KeyboardModifier.ControlModifier
            ):
                QApplication.quit()
            return True
        else:
            return super().eventFilter(obj, event)

    @Slot(Frame)
    def update_frame(self, frame: Frame) -> None:
        if not self.isVisible():
            return

        image = frame.image
        height, width, channels = image.shape
        # logger.info(f"Frame {frame.frame_id} {width} x {height} x {channels}")
        bytes_per_line = channels * width

        if frame.frame_id == 0:
            self.ui.video_label.setMinimumSize(QSize(width, height))
            logger.info(f"Frame size: {width}x{height}")

        self._camera_frame_id = frame.frame_id

        qimage = QImage(
            image.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_BGR888,
        ).copy()

        pixmap = QPixmap.fromImage(qimage)
        self.ui.video_label.setPixmap(pixmap)

        coords: tuple[ColoredQRect, ...] = faces_to_qrects_with_colors(
            self._face_detection_result.faces, pixmap.width(), pixmap.height()
        )

        ts_ns = frame.timestamp_ns if frame else 0
        self.ui.video_label.set_detections(coords, ts_ns, True)

    @Slot(FaceDetectionResult)
    def update_face_recognition(self, detection_result: FaceDetectionResult) -> None:
        self._face_detection_result = detection_result
        if len(detection_result.faces):
            self.ui.smile_label.setText("😐")
        else:
            self.ui.smile_label.setText("🖖")  # ("👾")

    @Slot(FaceDetectionResult)
    def update_smile_status(self, smile_status: SmileDetectionResult) -> None:
        pass

    @Slot(str)
    def camera_worker_error(self, msg: str) -> None:
        QMessageBox.critical(
            self, "Camera Error", f"{msg}\n\nPlease check camera connection and restart."
        )

    @Slot(type(BaseException), BaseException, str)
    def smile_worker_error(
        self, ex_type: type[BaseException], ex: BaseException, traceback: TracebackType
    ) -> None:
        self.ui.statusbar.showMessage("⚠ Smile Worker Error. Please check log for details.")

    @Slot(str, int)
    def smile_worker_progress(self, thread_name: str, smile_frame_id: int) -> None:
        # ToDo: Display diff with camera.frame_id?.. Have to think.
        self.ui.statusbar.showMessage(
            f"Smile Worker delay (in frames): {self._camera_frame_id - smile_frame_id}"
        )
