import logging
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication

from smile.camera.camera_worker import CameraWorker
from smile.recognition.detectors.face_recognition_worker import FaceRecognitionWorker
from smile.recognition.detectors.smile_recognition_worker import SmileRecognitionWorker
from smile.windows.main_window import MainWindow

logger = logging.getLogger(__name__)

__FACE_MODEL_PATH__ = (
    Path(__file__).resolve().parent / "recognition" / "models" / "blaze_face_short_range.tflite"
)

__LANDMARKER_MODEL_PATH__ = (
    Path(__file__).resolve().parent / "recognition" / "models" / "face_landmarker.task"
)


class SmileApp(QApplication):
    stop_camera = Signal()
    stop_recognition = Signal()
    stop_smile = Signal()

    def __init__(self, args: list[str]):
        super().__init__(args)

        logger.info("Creating the Smile application")

        self.camera_worker = CameraWorker()
        self.camera_thread = QThread()
        self.camera_worker.moveToThread(self.camera_thread)

        self.recognition_worker = FaceRecognitionWorker(__FACE_MODEL_PATH__)
        self.recognition_thread = QThread()
        self.recognition_worker.moveToThread(self.recognition_thread)

        self.smile_worker = SmileRecognitionWorker(__LANDMARKER_MODEL_PATH__)
        self.smile_thread = QThread()
        self.smile_worker.moveToThread(self.smile_thread)

        self.window = MainWindow()

        self.camera_thread.started.connect(self.camera_worker.wakeup)
        self.camera_worker.frame_ready.connect(self.window.update_frame)
        self.camera_worker.frame_ready.connect(self.recognition_worker.update_frame)

        self.recognition_thread.started.connect(self.recognition_worker.wakeup)
        self.recognition_worker.recognition_ready.connect(self.window.update_face_recognition)

        self.smile_thread.started.connect(self.smile_worker.wakeup)
        self.smile_worker.smile_status_ready.connect(self.window.update_smile_status)
        self.recognition_worker.recognition_ready.connect(self.smile_worker.update_recognition_result)

        self.stop_smile.connect(self.smile_worker.shutdown)
        self.stop_recognition.connect(self.recognition_worker.shutdown)
        self.stop_camera.connect(self.camera_worker.shutdown)

        self.aboutToQuit.connect(self.shutdown)

        self.smile_thread.finished.connect(self.smile_thread.deleteLater)
        self.camera_thread.finished.connect(self.camera_worker.deleteLater)
        self.recognition_thread.finished.connect(self.recognition_worker.deleteLater)

        self.camera_worker.camera_error.connect(self.window.camera_worker_error)

        self.window.show()

        self.smile_thread.start()
        self.recognition_thread.start()
        self.camera_thread.start()

        logger.info("The Smile application created")

    @Slot()
    def shutdown(self) -> None:
        logger.info("Application shutting down")

        self.stop_camera.emit()
        self.stop_recognition.emit()
        self.stop_smile.emit()

        QCoreApplication.processEvents()

        self.camera_thread.quit()
        self.recognition_thread.quit()
        self.smile_thread.quit()

        if not self.camera_thread.wait(3000):
            logger.warning("Camera thread did not stop")

        if not self.recognition_thread.wait(3000):
            logger.warning("Recognition thread did not stop")

        if not self.recognition_thread.wait(3000):
            logger.warning("Recognition thread did not stop")

        logger.info("Application shutdown process completed")
