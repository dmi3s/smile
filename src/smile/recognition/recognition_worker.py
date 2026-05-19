import logging

# import cv2
from PySide6.QtCore import QObject, Signal, Slot

from smile.camera.frame import Frame

logger = logging.getLogger(__name__)


class RecognitionWorker(QObject):
    frame_ready = Signal(Frame)
    error = Signal(str)
    # finished = Signal()

    def __init__(self) -> None:
        super().__init__()

    @Slot(Frame)
    def process_frame(self, frame: Frame) -> None:
        try:
            self.frame_ready.emit(frame)
        except Exception:
            logger.exception("Fail")

    @Slot()
    def stop(self) -> None:
        # self.finished.emit()
        logger.info("Stopped")

    @Slot()
    def start(self) -> None:
        logger.info("Started")
