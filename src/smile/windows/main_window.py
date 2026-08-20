import logging
from datetime import datetime
from pathlib import Path
from typing import cast, override

from PySide6.QtCore import QEvent, QObject, QSize, Qt, Slot
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QMainWindow

from smile.camera.frame import Frame
from smile.recognition.detectors.face_detection import FaceDetectionResult
from smile.recognition.detectors.flashlight_detection import (
    FlashlightDetectionResult,
)
from smile.recognition.detectors.smile_detection import SmileDetectionResult
from smile.ui.generated.ui_main_window import Ui_MainWindow
from smile.utils.fps_meter import FpsMeter
from smile.utils.smooth import ExponentialJitterSmoother

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path.home() / "Pictures" / "smile"


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
        self._flashlight_result = FlashlightDetectionResult(
            detected=False,
            score=0.0,
            bright_bbox=None,
            brightness=0.0,
            frame_id=-1,
        )
        self.installEventFilter(self)
        self._smile_smoother = ExponentialJitterSmoother(alpha=0.3)
        self._fps_capture = FpsMeter()
        self._fps_face = FpsMeter()
        self._fps_smile = FpsMeter()
        self._fps_render = FpsMeter()
        self._smile_status_text = "🖖"
        self.ui.video_label.rendered.connect(self._on_rendered)

        self.ui.screenshot_button.clicked.connect(self._take_screenshot)

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
        return super().eventFilter(obj, event)

    def _take_screenshot(self) -> None:
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Cannot create screenshot directory: {e}")
            self.ui.statusbar.showMessage("⚠ Cannot create screenshot directory")
            return

        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = SCREENSHOT_DIR / f"smile-{stamp}.png"
        counter = 1
        while path.exists():
            path = SCREENSHOT_DIR / f"smile-{stamp}-{counter}.png"
            counter += 1

        pixmap = self.grab()
        if not pixmap.save(str(path)):
            logger.error("Failed to save screenshot")
            self.ui.statusbar.showMessage("⚠ Screenshot save failed")
            return

        logger.info(f"Screenshot saved: {path}")
        self.ui.statusbar.showMessage(f"Saved {path.name}")

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
            (
                self._flashlight_result.bright_bbox
                if self._flashlight_result.detected
                else None
            ),
        )
        self._fps_capture.update(frame.timestamp_ns)
        self._refresh_statusbar()

    @Slot(FaceDetectionResult)
    def update_face_recognition(self, detection_result: FaceDetectionResult) -> None:
        self._fps_face.update()
        self._face_detection_result = detection_result

    @Slot(FlashlightDetectionResult)
    def update_flashlight(self, result: FlashlightDetectionResult) -> None:
        self._flashlight_result = result
        self._refresh_statusbar()

    @Slot(SmileDetectionResult)
    def update_smile_status(self, smile_status: SmileDetectionResult) -> None:
        logger.debug(f"update_smile_status: {smile_status.smile_scores}")
        self._fps_smile.update()
        if not smile_status.smile_scores:
            self._smile_smoother.reset()
            emoji = "🖖"
            self._smile_status_text = "🖖 no face"
        else:
            best = self._smile_smoother.update(max(smile_status.smile_scores))
            if best >= 0.60:
                emoji = "😄"
            elif best >= 0.15:
                emoji = "😊"
            else:
                emoji = "😐"
            self._smile_status_text = f"{emoji} smile={best:.2f}"
        self.ui.smile_label.setText(emoji)
        self._refresh_statusbar()

    def _refresh_statusbar(self) -> None:
        flashlight = (
            f"🔦 {self._flashlight_result.score:.2f}"
            if self._flashlight_result.detected
            else "🔦 —"
        )
        fps_text = (
            f"cam {self._fps_capture.fps:.0f} · "
            f"face {self._fps_face.fps:.0f} · "
            f"smile {self._fps_smile.fps:.0f} · "
            f"render {self._fps_render.fps:.0f} fps"
        )
        self.ui.statusbar.showMessage(
            f"{self._smile_status_text}  |  {flashlight}  |  {fps_text}"
        )

    @Slot()
    def _on_rendered(self) -> None:
        self._fps_render.update()

    @Slot(str)
    def camera_worker_error(self, msg: str) -> None:
        self.ui.statusbar.showMessage(f"⚠ Camera lost: {msg} — reconnecting …")

    @Slot()
    def camera_recovered(self) -> None:
        self.ui.statusbar.showMessage("📷 Camera reconnected", 3000)

    @Slot(type(BaseException), BaseException, str)
    def smile_worker_error(
        self, ex_type: type[BaseException], ex: BaseException, traceback: str
    ) -> None:
        logger.error("Smile worker error: %s: %s\n%s", ex_type.__name__, ex, traceback)
        self.ui.statusbar.showMessage(f"⚠ Smile Worker Error: {ex_type.__name__}")

    @Slot(type(BaseException), BaseException, str)
    def flashlight_worker_error(
        self, ex_type: type[BaseException], ex: BaseException, traceback: str
    ) -> None:
        logger.error(
            "Flashlight worker error: %s: %s\n%s", ex_type.__name__, ex, traceback
        )
        self.ui.statusbar.showMessage(f"⚠ Flashlight Worker Error: {ex_type.__name__}")
