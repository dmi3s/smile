import logging
import traceback
from pathlib import Path
from typing import cast

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.components.containers.detections import DetectionResult
from numpy._typing import NDArray
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from smile.camera.frame import Frame
from smile.recognition.detectors.face_detection import DetectedFaceBox, FaceBox, FaceDetectionResult
from smile.utils.latest_value_mailbox import LatestValueMailbox

logger = logging.getLogger(__name__)

class FaceDetectionWorker(QObject):
    """
    Worker that runs SMILE detection tasks

    Signals from a running worker thread.
        result
            object data returned from processing: FaceDetectionResult
        progress
            tuple (str, frame_id)
        finished
            str thread name
        error
            tuple (exctype, value, traceback.format_exc())
    """


    result = Signal(FaceDetectionResult)
    progress = Signal(str, int)
    error = Signal(type[BaseException], BaseException, str)
    finished = Signal(str)

    def __init__(self, model_path: Path) -> None:
        super().__init__()
        self._model_path: Path = model_path
        self._detector: vision.FaceDetector | None = None
        self._mailbox = LatestValueMailbox[Frame]()

        thread_name: str = QThread.currentThread().objectName()
        logger.info(f'Created on thread "{thread_name}"')
        logger.info(f"Init with {model_path=}")

    @Slot()
    def wakeup(self):
        thread_name : str = QThread.currentThread().objectName()
        logger.info(f"Waking up on thread \"{thread_name}\"")

        try:
            opts = python.BaseOptions(
                model_asset_path=str(self._model_path)
            )
            options = vision.FaceDetectorOptions(
                base_options=opts,
                min_detection_confidence=0.5,
                running_mode=vision.RunningMode.VIDEO,
            )
            self._detector = vision.FaceDetector.create_from_options(options)
            self._mailbox.wakeup()
        except Exception as e:
            self.error.emit(type(e), e,  traceback.format_exc())
            logger.error(f"Init failed: {e}")
            return

        logger.info("Started")

    def _cleanup(self):
        assert not self._mailbox.busy
        if self._detector:
            self._detector.close()
            self._detector = None

    @Slot()
    def shutdown(self):
        self._mailbox.shutdown()
        self._cleanup()
        self.finished.emit(QThread.currentThread().objectName())
        logger.info("Stopped")

    @Slot(Frame)
    def new_frame(self, frame: Frame) -> None:
        self._mailbox.new_data(frame)

        if self._mailbox.try_start():
            QTimer.singleShot(0, self._process_next)

    # NOTE: In this version of MediaPipe Tasks API (0.10+), FaceDetector with
    # RunningMode.VIDEO returns bounding box coordinates in absolute pixels
    # relative to the input image dimensions (small_data), NOT normalized [0,1].
    # If behavior changes in future versions, check the heuristic in _construct_recognition_result.
    @staticmethod
    def _construct_recognition_result(
        detection_result: DetectionResult,
        x_scale: float,
        y_scale: float,
        frame_rgb: Frame,
    ) -> FaceDetectionResult:

        faces: list[DetectedFaceBox] = []
        for detection in detection_result.detections:
            assert detection.categories[0].score
            # Normalize coords to [0,1]
            faces.append(
                DetectedFaceBox(
                    bbox=FaceBox(
                        detection.bounding_box.origin_x * x_scale,
                        detection.bounding_box.origin_y * y_scale,
                        detection.bounding_box.width * x_scale,
                        detection.bounding_box.height * y_scale,
                    ),
                    score=detection.categories[0].score
                )
            )

        return FaceDetectionResult(
            faces= tuple(faces),
            frame_bgr= frame_rgb
        )

    @Slot()
    def _process_next(self):
        frame = self._mailbox.extract_data()

        assert frame is not None

        try:
            small_data = cv2.resize(
                frame.image,
                dsize = (0, 0),
                fx = 0.5, fy = 0.5,
                interpolation=cv2.INTER_AREA
            )

            small_data = cast(
                NDArray,
                cv2.cvtColor(small_data, cv2.COLOR_BGR2RGB)
            )
            # small_data = np.ascontiguousarray(small_data[:, :, ::-1])

            image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=small_data
            )

            assert self._detector
            result = self._detector.detect_for_video(
                image,
                frame.timestamp_ns // 1_000_000
            )

            result = FaceDetectionWorker._construct_recognition_result(
                result,
                1.0 / image.width,
                1.0 / image.height,
                frame
            )

        except BaseException as e:
            exctype: type  = type(e)
            tb: str = traceback.format_exc()
            self.error.emit(exctype, e, tb)
            logger.error(f"Processing failed: {e}\n{tb}")
        else:
            self.result.emit(result)
            self.progress.emit(QThread.currentThread().objectName(), frame.frame_id)
        finally:
            if self._mailbox.complete_and_should_continue():
                QTimer.singleShot(0, self._process_next)
