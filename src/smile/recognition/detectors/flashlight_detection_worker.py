import logging
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PySide6.QtCore import Signal, Slot

from smile.camera.frame import Frame
from smile.recognition.detectors.flashlight_detection import (
    Category,
    FlashlightDetectionResult,
    detect_bright_spot,
    hybrid_flashlight_result,
    is_flashlight,
)
from smile.utils.mailbox_worker import MailboxWorker

logger = logging.getLogger(__name__)


class FlashlightDetectionWorker(MailboxWorker):
    """Runs the ImageNet classifier plus a bright-spot heuristic per frame.

    Signals from a running worker thread.
        result
            FlashlightDetectionResult
        error
            (exctype, value, traceback.format_exc())
    """

    result = Signal(FlashlightDetectionResult)

    def __init__(self, model_path: Path) -> None:
        super().__init__()
        self._model_path = model_path
        self._classifier: vision.ImageClassifier | None = None

        logger.info(f"Init with {model_path=}")

    def _init_worker(self) -> None:
        options = vision.ImageClassifierOptions(
            base_options=python.BaseOptions(model_asset_path=str(self._model_path)),
            running_mode=vision.RunningMode.VIDEO,
            max_results=5,
        )
        self._classifier = vision.ImageClassifier.create_from_options(options)

    def _cleanup(self) -> None:
        super()._cleanup()
        if self._classifier is not None:
            self._classifier.close()
            self._classifier = None

    @Slot(Frame)
    def new_frame(self, frame: Frame) -> None:
        self._enqueue(frame)

    def _process(self, frame: Frame) -> None:
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

        classifier_detected, classifier_score = is_flashlight(categories)
        spot = detect_bright_spot(small_rgb)

        result = hybrid_flashlight_result(
            classifier_detected,
            classifier_score,
            spot,
            frame.frame_id,
        )
        self.result.emit(result)
