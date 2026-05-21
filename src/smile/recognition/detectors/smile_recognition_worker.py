import logging
from pathlib import Path

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PySide6.QtCore import QObject, QTimer, Signal, Slot

from smile.recognition.detectors.smile_detection import RecognitionResult
from smile.utils.latest_value_mailbox import LatestValueMailbox

logger = logging.getLogger(__name__)

class SmileRecognitionWorker(QObject):
    smile_status_ready = Signal(RecognitionResult)
    error = Signal(str)

    def __init__(self, model_path: Path):
        super().__init__()
        self._model_path = model_path
        self._detector = None
        self._mailbox = LatestValueMailbox[RecognitionResult]()

    @Slot()
    def wakeup(self) -> None:
        logger.info("Starting ...")
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
            self.error.emit(f"Init failed: {e}")
            logger.error(f"Init failed: {e}")
            return
        logger.info("Started")

    def _cleanup(self):
        assert not self._mailbox.busy
        self._detector.close()
        self._detector = None

    @Slot()
    def shutdown(self) -> None:
        self._mailbox.shutdown()
        self._cleanup()
        logger.info("Stopped")

    @Slot(RecognitionResult)
    def update_recognition_result(self, rec: RecognitionResult) -> None:
        self._mailbox.new_data(rec)
        if self._mailbox.try_start():
            QTimer.singleShot(0, self._process_next)

    @Slot()
    def remove_me(self) -> None:
        pass

    @Slot()
    def _process_next(self) -> None:
        rec = self._mailbox.extract_data()

        try:
            QTimer.singleShot(60_000, self.remove_me)
            logger.info(f"Processing: {rec.faces}")

        except Exception as e:
            self.error.emit(f"Processing failed: {e}")
            logger.error(f"Processing failed: {e}")

        if self._mailbox.complete_and_should_continue():
            QTimer.singleShot(0, self._process_next)
