import logging
from pathlib import Path

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PySide6.QtCore import Signal, Slot

from smile.recognition.detectors.face_detection import FaceDetectionResult
from smile.recognition.detectors.smile_detection import (
    SmileDetectionResult,
    smile_score,
)
from smile.utils.mailbox_worker import MailboxWorker

logger = logging.getLogger(__name__)


class SmileDetectionWorker(MailboxWorker):
    """
    Worker that runs SMILE detection tasks

    Signals from a running worker thread.
        result
            object data returned from processing: SmileDetectionResult
        error
            (exctype, value, traceback.format_exc())
    """

    result = Signal(SmileDetectionResult)

    def __init__(self, model_path: Path):
        super().__init__()
        self._model_path = model_path
        self._detector: vision.FaceLandmarker | None = None

        logger.info(f"Init with {model_path=}")

    def _init_worker(self) -> None:
        opts = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(self._model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=4,
            min_face_detection_confidence=0.5,
        )
        self._detector = vision.FaceLandmarker.create_from_options(opts)

    def _cleanup(self) -> None:
        super()._cleanup()
        if self._detector is not None:
            self._detector.close()
            self._detector = None

    @Slot(FaceDetectionResult)
    def new_face_detection_result(self, rec: FaceDetectionResult) -> None:
        self._enqueue(rec)

    def _process(self, rec: FaceDetectionResult) -> None:
        if rec.small_frame_rgb is None:
            self.error.emit(
                ValueError,
                ValueError("rec.small_frame_rgb is None"),
                "_process()",
            )
            logger.error("_process() received empty rec.small_frame_rgb")
            return

        assert self._detector is not None

        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rec.small_frame_rgb.image,
        )
        landmarker_result = self._detector.detect_for_video(
            image,
            rec.small_frame_rgb.timestamp_ns // 1_000_000,
        )
        scores = tuple(smile_score(face) for face in landmarker_result.face_landmarks)
        result = SmileDetectionResult(smile_scores=scores, frame_id=rec.frame_id)
        self.result.emit(result)
