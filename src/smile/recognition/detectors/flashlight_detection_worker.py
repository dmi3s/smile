import logging
import traceback
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from smile.camera.frame import Frame
from smile.recognition.detectors.flashlight_detection import (
    Category,
    FlashlightDetectionResult,
    detect_bright_spot,
    is_flashlight,
)
from smile.utils.latest_value_mailbox import LatestValueMailbox

logger = logging.getLogger(__name__)


class FlashlightDetectionWorker(QObject):
    """Runs the ImageNet classifier plus a bright-spot heuristic per frame.

    Signals from a running worker thread.
        result
            FlashlightDetectionResult
        progress
            (str, frame_id)
        error
            (exctype, value, traceback.format_exc())
    """

    result = Signal(FlashlightDetectionResult)
    error = Signal(type(BaseException), BaseException, str)
    progress = Signal(str, int)

    def __init__(self, model_path: Path) -> None:
        super().__init__()
        self._model_path = model_path
        self._classifier: vision.ImageClassifier | None = None
        self._mailbox = LatestValueMailbox[Frame]()

        thread_name: str = QThread.currentThread().objectName()
        logger.info(f'Created on thread "{thread_name}"')
        logger.info(f"Init with {model_path=}")

    @Slot()
    def wakeup(self):
        thread_name: str = QThread.currentThread().objectName()
        logger.info(f'Waking up on thread "{thread_name}"')

        try:
            options = vision.ImageClassifierOptions(
                base_options=python.BaseOptions(model_asset_path=str(self._model_path)),
                running_mode=vision.RunningMode.VIDEO,
                max_results=5,
            )
            self._classifier = vision.ImageClassifier.create_from_options(options)
            self._mailbox.wakeup()
        except Exception as e:
            self.error.emit(type(e), e, traceback.format_exc())
            logger.error(f"Init failed: {e}")
            return

        logger.info("Started")

    def _cleanup(self):
        assert not self._mailbox.busy
        if self._classifier is not None:
            self._classifier.close()
            self._classifier = None

    @Slot()
    def shutdown(self):
        self._mailbox.shutdown()
        self._cleanup()
        logger.info("Stopped")

    @Slot(Frame)
    def new_frame(self, frame: Frame) -> None:
        self._mailbox.new_data(frame)

        if self._mailbox.try_start():
            QTimer.singleShot(0, self._process_next)

    @Slot()
    def _process_next(self) -> None:
        frame = self._mailbox.extract_data()

        assert frame is not None

        try:
            small = cv2.resize(
                frame.image,
                dsize=(0, 0),
                fx=0.5,
                fy=0.5,
                interpolation=cv2.INTER_AREA,
            )
            small_rgb = np.ascontiguousarray(small[:, :, ::-1])
            small_rgb.flags.writeable = False

            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=small_rgb)

            assert self._classifier
            classification = self._classifier.classify_for_video(
                image, frame.timestamp_ns // 1_000_000
            )

            categories = tuple(
                Category(
                    index=cat.index,
                    score=cat.score,
                    name=cat.category_name or "",
                )
                for cat in classification.classifications[0].categories
            )

            detected, score = is_flashlight(categories)
            spot = detect_bright_spot(small_rgb)

            result = FlashlightDetectionResult(
                detected=detected,
                score=score,
                bright_bbox=spot.bbox if spot is not None else None,
                brightness=spot.peak if spot is not None else 0.0,
                frame_id=frame.frame_id,
            )

        except BaseException as e:
            exctype: type = type(e)
            tb: str = traceback.format_exc()
            self.error.emit(exctype, e, tb)
            logger.error(f"Processing failed: {e}\n{tb}")
        else:
            self.result.emit(result)
            self.progress.emit(QThread.currentThread().objectName(), frame.frame_id)
        finally:
            if self._mailbox.complete_and_should_continue():
                QTimer.singleShot(0, self._process_next)
