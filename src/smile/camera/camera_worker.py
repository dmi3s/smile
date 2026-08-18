import logging
import time

import cv2
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from smile.camera.frame import Frame

logger = logging.getLogger(__name__)


class CameraWorker(QObject):
    CAMERA_INDEX: int = 0
    FRAME_WIDTH: int = 800
    FRAME_HEIGHT: int = 448
    FRAME_FPS: int = 20

    frame_ready = Signal(Frame)
    camera_error = Signal(str)
    camera_started = Signal()

    def __init__(self):
        super().__init__()
        self._frame_count = 0
        self._timer: QTimer | None = QTimer(self)
        self._timer.timeout.connect(self._capture_frame)
        self._cap: cv2.VideoCapture | None = None
        self._stopping = False
        thread_name: str = QThread.currentThread().objectName()
        logger.info(f'Created on thread "{thread_name}"')

    @Slot()
    def wakeup(self) -> None:
        thread_name: str = QThread.currentThread().objectName()
        logger.info(f'Waking up on thread "{thread_name}"')

        self._cap = cv2.VideoCapture(CameraWorker.CAMERA_INDEX)

        if self._cap is None or not self._cap.isOpened():
            logger.error("Cannot open default camera")
            self.camera_error.emit("Cannot open default camera")
            return

        self._setup_camera()

        self.camera_started.emit()

        logger.info("Started")

    def _setup_camera(self) -> None:
        if self._cap is None:
            logger.error("Camera capture is not initialized")
            return
        if not self._cap.isOpened():
            logger.error("Camera is not opened")
            return

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, CameraWorker.FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CameraWorker.FRAME_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, CameraWorker.FRAME_FPS)
        fps: int = int(self._cap.get(cv2.CAP_PROP_FPS))

        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        backend: str = self._cap.getBackendName()
        logger.info(f"Camera mode: {w}x{h} @ {fps} ({backend=})")

        if not 0 < fps <= 1000:
            logger.warning(
                f"Invalid camera FPS: {fps}; falling back to {CameraWorker.FRAME_FPS}"
            )
            fps = CameraWorker.FRAME_FPS

        if self._timer is None:
            logger.error("Timer is not initialized")
            return

        self._timer.start(1000 // fps)

    @Slot()
    def _capture_frame(self) -> None:
        if self._stopping:
            return
        if self._cap is None:
            return

        ret, bgr_frame = self._cap.read()

        if not ret:
            logger.warning("Failed to read frame")
            self.camera_error.emit("Failed to read frame")
            return

        timestamp_ns = time.monotonic_ns()

        frame = Frame.create_copy(bgr_frame, self._frame_count, timestamp_ns)
        bgr_frame.flags.writeable = False

        self._frame_count += 1

        self.frame_ready.emit(frame)

    @Slot()
    def shutdown(self) -> None:
        self._stopping = True
        self._frame_count = 0

        if self._timer is not None:
            self._timer.stop()
            self._timer = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

        logger.info("Stopped")
