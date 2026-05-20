import logging
import time

import cv2
import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal, Slot

from smile.camera.frame import Frame

logger = logging.getLogger(__name__)


class CameraWorker(QObject):
    frame_ready = Signal(Frame)
    error = Signal(str)
    camera_started = Signal()
    # ToDo:
    # stop_camera = Signal()
    # fps_updated = Signal()
    # camera_disconnected = Signal()

    def __init__(self):
        super().__init__()
        self._frame_id = 0
        self._timer = None
        self._cap = None
        self._stopping = False
        logger.info("Created")

    @Slot()
    def start(self) -> None:
        logger.info("Starting")
        self._cap = cv2.VideoCapture(0)

        if not self._cap.isOpened():
            logger.error("Cannot open camera")
            self.error.emit("Cannot open camera")
            return

        self.camera_started.emit()

        self._timer = QTimer(self)
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
            self.error.emit("Failed to read frame")
            return

        timestamp_ns = time.monotonic_ns()
        # rgb_image = cast(
        #     NDArray,
        #     cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        # )
        rgb_image = np.ascontiguousarray(bgr_frame[:, :, ::-1])

        frame = Frame.from_owned(rgb_image, self._frame_id, timestamp_ns)

        self._frame_id += 1
        self.frame_ready.emit(frame)

    @Slot()
    def stop(self) -> None:
        logger.info("Stopping")
        self._stopping = True

        if self._timer is not None:
            self._timer.stop()
            self._timer = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

        logger.info("Stopped")
