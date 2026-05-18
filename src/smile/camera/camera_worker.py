import logging
import time

import cv2
from PySide6.QtCore import QObject, QTimer, Signal, Slot

from smile.camera.frame import Frame

logger = logging.getLogger(__name__)


class CameraWorker(QObject):
    frame_ready = Signal(Frame)
    # finished = Signal()
    error = Signal(str)
    camera_started = Signal()
    stop_camera = Signal()
    # ToDo:
    fps_updated = Signal()
    camera_disconnected = Signal()

    def __init__(self):
        super().__init__()
        logger.info("Created")

    @Slot()
    def start(self) -> None:
        logger.info("Started")

        self._cap = cv2.VideoCapture(0)

        if not self._cap.isOpened():
            logger.error("Cannot open camera")
            self.error.emit("Cannot open camera")
            return

        self.camera_started.emit()
        self._frame_id = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._capture_frame)
        self._timer.start(33)  # about 30 fps

    @Slot()
    def _capture_frame(self) -> None:
        ret, frame = self._cap.read()
        if not ret:
            logger.error("Failed to read frame")
            return

        vframe = Frame.from_copy(frame, self._frame_id, 0.0)
        self._frame_id += 1
        self.frame_ready.emit(vframe)

    @Slot()
    def stop(self) -> None:
        logger.info("Stopping")

        if self._timer is not None:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

        logger.info("Stopped")
