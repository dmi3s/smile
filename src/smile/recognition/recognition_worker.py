import logging

import cv2
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from smile.camera.frame import Frame

logger = logging.getLogger(__name__)


class RecognitionWorker(QObject):
    qimage_ready = Signal(QImage)
    error = Signal(str)
    # finished = Signal()

    def __init__(self) -> None:
        super().__init__()

    @Slot(Frame)
    def process_frame(self, frame: Frame) -> None:
        try:
            image = frame.image

            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            height, width, channels = rgb.shape

            # logger.info(f"Frame {frame.frame_id} {width} x {height} x {channels}")

            bytes_per_line = channels * width

            qimage = QImage(
                rgb.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            )

            self.qimage_ready.emit(qimage)

        except Exception:
            logger.exception("Fail")

    @Slot()
    def stop(self) -> None:
        # self.finished.emit()
        logger.info("Stopped")

    @Slot()
    def start(self) -> None:
        logger.info("Started")
