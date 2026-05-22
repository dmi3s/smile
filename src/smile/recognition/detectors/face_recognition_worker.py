import logging
from pathlib import Path
from typing import cast

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.components.containers.detections import DetectionResult
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from numpy._typing import NDArray

from smile.camera.frame import Frame
from smile.recognition.detectors.face_detection import DetectedFaceBox, FaceBox, RecognitionResult

logger = logging.getLogger(__name__)

class FaceRecognitionWorker(QObject):
    recognition_ready = Signal(RecognitionResult)
    error = Signal(str)

    def __init__(self, model_path: Path) -> None:
        super().__init__()
        self._model_path: Path = model_path
        self._detector: vision.FaceDetector | None = None
        self._latest_frame: Frame | None = None
        self._busy = False
        self._stopping = False
        
        thread_name: str = QThread.currentThread().objectName()
        logger.info(f'Created on thread "{thread_name}"')
        logger.info(f"Init with {model_path=}")

    @Slot()
    def wakeup(self):
        try:
            base_options = python.BaseOptions(
                model_asset_path=str(self._model_path)
            )
            options = vision.FaceDetectorOptions(
                base_options=base_options,
                min_detection_confidence=0.5,
                running_mode=vision.RunningMode.VIDEO,
            )
            self._detector = vision.FaceDetector.create_from_options(options)
        except Exception as e:
            self.error.emit(str(e))
            logger.error(str(e))
        logger.info("Started")

    @Slot(Frame)
    def update_frame(self, frame: Frame) -> None:
        self._latest_frame = frame
        if not self._busy:
            self._busy = True
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
    ) -> RecognitionResult:

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

        return RecognitionResult(
            faces= tuple(faces),
            frame_bgr= frame_rgb
        )

    @Slot()
    def _process_next(self):
        if self._stopping:
            self._busy = False
            return

        frame = self._latest_frame

        if frame is None:
            self._busy = False
            return

        self._latest_frame = None

        try:
            small_data = cv2.resize(
                frame.image,
                dsize = (0, 0),
                fx = 0.5, fy = 0.5,
                interpolation=cv2.INTER_AREA
            )
            # Not sure
            # small_data = np.ascontiguousarray(small_data)

            small_data = cast(
                NDArray,
                cv2.cvtColor(small_data, cv2.COLOR_BGR2RGB)
            )

            image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=small_data
            )

            assert self._detector
            result = self._detector.detect_for_video(
                image,
                frame.timestamp_ns // 1_000_000
            )

            result = FaceRecognitionWorker._construct_recognition_result(
                result,
                1.0 / image.width,
                1.0 / image.height,
                frame
            )

            self.recognition_ready.emit(result)

        except Exception as e:
            self.error.emit(str(e))
            logger.error(str(e))
        finally:
            if self._stopping:
                self._busy = False
                self._cleanup()
            elif self._latest_frame is not None:
                QTimer.singleShot(0, self._process_next)
            else:
                self._busy = False

    @Slot()
    def shutdown(self):
        self._stopping = True
        self._latest_frame = None

        if not self._busy:
            self._cleanup()
        logger.info("Stopped")

    def _cleanup(self):
        if self._detector:
            self._detector.close()
            self._detector = None
