import logging

# from asyncio import SendfileNotAvailableError
import time

import cv2
from PySide6.QtCore import QObject, Signal, Slot

from smile.camera.frame import Frame

logger = logging.getLogger(__name__)


class CameraWorker(QObject):
    frame_ready = Signal(Frame)
    finished = Signal()
    error = Signal(str)
    camera_started = Signal()
    # ToDo:
    fps_updated = Signal()
    camera_disconnected = Signal()

    def __init__(self):
        super().__init__()
        logger.info("Camera worker created")
        self._running = False
        self._frame_id = 0

    @Slot()
    def start(self) -> None:
        logger.info("Started")

        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            logger.error("Cannot open camera")
            self.error.emit("Cannot open camera")
            self.finished.emit()
            return

        try:
            self._running = True
            self.camera_started.emit()

            while self._running:
                ret, frame = cap.read()

                if not ret:
                    logger.error("Failed tor read frame")
                    self.error.emit("Failed to read frame")
                    break

                vframe = Frame.from_copy(frame, self._frame_id, 0.0)
                self._frame_id += 1

                self.frame_ready.emit(vframe)

                time.sleep(0.03)

        except Exception:
            logger.exception("Open CV exception occured")
        finally:
            cap.release()
            logger.info("Camera worker stopped")
            self.finished.emit()

    @Slot()
    def stop(self) -> None:
        logger.info("Stopping Camera worker")

        self._running = False
