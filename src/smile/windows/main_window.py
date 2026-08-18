import logging
from typing import cast, override

from PySide6.QtCore import QEvent, QObject, QSize, Qt, Slot
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

from smile.camera.frame import Frame
from smile.recognition.detectors.face_detection import FaceDetectionResult
from smile.recognition.detectors.smile_detection import SmileDetectionResult
from smile.ui.generated.ui_main_window import Ui_MainWindow
from smile.utils.smooth import ExponentialJitterSmoother

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._face_detection_result = FaceDetectionResult(
            tuple(),
            small_frame_rgb=None,
            frame_id=-1,
        )
        self.installEventFilter(self)
        self._smile_smoother = ExponentialJitterSmoother(alpha=0.3)

    @override
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key_event = cast(QKeyEvent, event)
            logger.info(
                f"KeyPress: {key_event.key()} with modifiers= {key_event.modifiers()}"
            )
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
        height, width, _ = image.shape

        if frame.frame_id == 0:
            self.ui.video_label.setMinimumSize(QSize(width, height))
            logger.info(f"Frame size: {width}x{height}")

        self.ui.video_label.set_frame(
            image,
            self._face_detection_result.faces,
            frame.timestamp_ns,
            True,
        )

    @Slot(FaceDetectionResult)
    def update_face_recognition(self, detection_result: FaceDetectionResult) -> None:
        self._face_detection_result = detection_result

    @Slot(SmileDetectionResult)
    def update_smile_status(self, smile_status: SmileDetectionResult) -> None:
        logger.debug(f"update_smile_status: {smile_status.smile_scores}")
        if not smile_status.smile_scores:
            self._smile_smoother.reset()
            self.ui.smile_label.setText("🖖")
            self.ui.statusbar.showMessage("🖖 no face")
            return
        best = self._smile_smoother.update(max(smile_status.smile_scores))
        if best >= 0.60:
            emoji = "😄"
        elif best >= 0.20:
            emoji = "😊"
        else:
            emoji = "😐"
        self.ui.smile_label.setText(emoji)
        self.ui.statusbar.showMessage(f"{emoji} smile={best:.2f}")

    @Slot(str)
    def camera_worker_error(self, msg: str) -> None:
        QMessageBox.critical(
            self,
            "Camera Error",
            f"{msg}\n\nPlease check camera connection and restart.",
        )

    @Slot(type(BaseException), BaseException, str)
    def smile_worker_error(
        self, ex_type: type[BaseException], ex: BaseException, traceback: str
    ) -> None:
        self.ui.statusbar.showMessage(
            "⚠ Smile Worker Error. Please check log for details."
        )

    @Slot(str, int)
    def smile_worker_progress(self, thread_name: str, smile_frame_id: int) -> None:
        # ToDo: Display diff with camera.frame_id?.. Have to think.
        # Deliberately does not touch the status bar: it would overwrite the
        # smile score shown by update_smile_status.
        pass
