import logging

import cv2
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from smile.camera.frame import Frame

logger = logging.getLogger(__name__)


class RecognitionWorker(QObject):
    qimage_ready = Signal(QImage)
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()

    @Slot(Frame)
    def process_frame(self, frame: Frame) -> None:
        try:
            image = frame.image

            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            height, width, channels = rgb.shape
            bytes_per_line = channels * width

            qimage = QImage(
                rgb.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            ).copy()

            self.qimage_ready.emit(qimage)

        except Exception:
            logger.exception("Recognition worker failed")

            self.error.emit("Recognition worker failed")

    @Slot()
    def stop(self) -> None:
        logger.info("Stopping recognition worker")

    @Slot()
    def start(self) -> None:
        logger.info("Starting recognition worker")
