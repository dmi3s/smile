import logging
import time

import cv2
import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal, Slot, QThread

from smile.camera.frame import Frame

logger = logging.getLogger(__name__)


class CameraWorker(QObject):
    frame_ready = Signal(Frame)
    camera_error = Signal(str)
    camera_started = Signal()
    # ToDo:
    # stop_camera = Signal()
    # fps_updated = Signal()
    # camera_disconnected = Signal()

    def __init__(self):
        super().__init__()
        self._frame_id = 0
        self._timer : QTimer | None= None
        self._cap : cv2.VideoCapture | None = None
        self._stopping = False
        thread_name : str = QThread.currentThread().objectName()
        logger.info(f"Created on thread \"{thread_name}\"")

    @Slot()
    def wakeup(self) -> None:
        logger.info("Starting")
        self._cap = cv2.VideoCapture(0)

        if not self._cap.isOpened():
            logger.error("Cannot open camera")
            self.camera_error.emit("Cannot open camera")
            return

        fps = self._cap.get(cv2.CAP_PROP_FPS)
        logger.info(f"{fps=}")

        self.camera_started.emit()

        self._timer = QTimer(self)
        assert self._timer is not None
        self._timer.timeout.connect(self._capture_frame)
        self._timer.start(33)  # about 30 fps

        logger.info("Started")


    @Slot()
    def _capture_frame(self) -> None:
        if self._stopping:
            return
        assert self._cap is not None
        ret, bgr_frame = self._cap.read()

        if not ret:
            logger.warning("Failed to read frame")
            self.camera_error.emit("Failed to read frame")
            return

        timestamp_ns = time.monotonic_ns()
        # rgb_image = cast(
        #     NDArray,
        #     cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        # )
        # or
        # rgb_image = np.ascontiguousarray(bgr_frame[:, :, ::-1])

        frame = Frame.from_copy(bgr_frame, self._frame_id, timestamp_ns)

        self._frame_id += 1
        self.frame_ready.emit(frame)

    @Slot()
    def shutdown(self) -> None:
        logger.info("Stopping")
        self._stopping = True

        if self._timer is not None:
            self._timer.stop()
            self._timer = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

        logger.info("Stopped")
