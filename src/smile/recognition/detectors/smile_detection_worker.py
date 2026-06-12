import logging
import traceback
from pathlib import Path

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PySide6 import QtTest
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from smile.recognition.detectors.face_detection import FaceDetectionResult
from smile.recognition.detectors.smile_detection import SmileDetectionResult
from smile.utils.latest_value_mailbox import LatestValueMailbox

logger = logging.getLogger(__name__)

class SmileDetectionWorker(QObject):
    """
    Worker that runs SMILE detection tasks

    Signals from a running worker thread.
        result
            object data returned from processing: SmileDetectionResult
        progress
            (str, frame_id)
        finished
            str thread name
        error
            (exctype, value, traceback.format_exc())
    """

    result = Signal(SmileDetectionResult)
    error = Signal(type[BaseException], BaseException, str)
    progress = Signal(str, int)
    finished = Signal(str)

    def __init__(self, model_path: Path):
        super().__init__()
        self._model_path = model_path
        self._detector = None
        self._mailbox = LatestValueMailbox[FaceDetectionResult]()

        thread_name: str = QThread.currentThread().objectName()
        logger.info(f'Created on thread "{thread_name}"')
        logger.info(f"Init with {model_path=}")


    @Slot()
    def wakeup(self) -> None:
        thread_name : str = QThread.currentThread().objectName()
        logger.info(f"Waking up on thread \"{thread_name}\"")
        try:
            opts = vision.FaceLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path= str(self._model_path)),
                running_mode=vision.RunningMode.VIDEO,
                num_faces=4,
                min_face_detection_confidence=0.5,
            )
            self._detector : vision.FaceLandmarker = (
                vision.FaceLandmarker.create_from_options(opts)
            )
            self._mailbox.wakeup()
        except Exception as e:
            self.error.emit(type(e), e, traceback.format_exc())
            logger.error(f"Init failed: {e}")
            return
        logger.info("Started")

    def _cleanup(self):
        assert not self._mailbox.busy
        if self._detector is not None:
            self._detector.close()
            self._detector = None

    @Slot()
    def shutdown(self) -> None:
        self._mailbox.shutdown()
        self._cleanup()
        self.finished.emit(QThread.currentThread().objectName())
        logger.info("Stopped")

    @Slot(FaceDetectionResult)
    def new_face_detection_result(self, rec: FaceDetectionResult) -> None:
        self._mailbox.new_data(rec)
        if self._mailbox.try_start():
            QTimer.singleShot(0, self._process_next)

    @Slot()
    def _process_next(self) -> None:
        rec = self._mailbox.extract_data()

        assert rec is not None
        
        if rec.small_frame_rgb is None:
            self.error.emit(
                ValueError,
                ValueError("rec.small_frame_rgb is None"),
                "_process_next()"
            )
            logger.error("_process_next() received empty rec.small_frame_rgb")
            return

        try:
            # SmileResult = RecognitionResult
            # ToDo: Replace this dummy code to real one
            # time.sleep(0.1)
            QtTest.QTest.qWait(69)
            result: SmileDetectionResult = rec
        except BaseException as e:
            exctype: type  = type(e)
            tb: str = traceback.format_exc()
            self.error.emit(exctype, e, tb)
            logger.error(f"Processing failed: {e}\n{tb}")
        else:
            self.result.emit(result)
            self.progress.emit(QThread.currentThread().objectName(), rec.camera_frame_id)
        finally:
            if self._mailbox.complete_and_should_continue():
                QTimer.singleShot(0, self._process_next)
