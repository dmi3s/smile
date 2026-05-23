import logging
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication

from smile.camera.camera_worker import CameraWorker
from smile.recognition.detectors.face_detection_worker import FaceDetectionWorker
from smile.recognition.detectors.smile_detection_worker import SmileDetectionWorker
from smile.windows.main_window import MainWindow

logger = logging.getLogger(__name__)

class SmileApp(QApplication):
    stop_camera = Signal()
    stop_face = Signal()
    stop_smile = Signal()

    _FACE_MODEL_PATH = (
        Path(__file__).resolve().parent / "recognition" / "models" / "blaze_face_short_range.tflite"
    )

    _LANDMARKER_MODEL_PATH = (
        Path(__file__).resolve().parent / "recognition" / "models" / "face_landmarker.task"
    )

    def __init__(self, args: list[str]):
        super().__init__(args)

        logger.info("Initializing ...")

        self._create_workers()

        self._setup_camera_worker()
        self._setup_face_worker()
        self._setup_smile_worker()

        self.aboutToQuit.connect(self.shutdown)

        # Let's go
        self._window.show()

        for th in self._threads:
            th.start()

        logger.info("Initialization completed")

    @Slot()
    def shutdown(self) -> None:
        logger.info("Shutting down ...")

        self.stop_camera.emit()
        self.stop_face.emit()
        self.stop_smile.emit()

        QCoreApplication.processEvents()

        for th in self._threads:
            th.quit()
            
        for th in self._threads:
            if not th.wait(3000):
                logger.warning(f"Thread \"{th.objectName()}\" did not stop.")

        logger.info("Shutdown completed")

    def _setup_smile_worker(self):
        self._smile_worker.result.connect(self._window.update_smile_status)
        self._smile_worker.error.connect(self._window.smile_worker_error)
        self._smile_worker.progress.connect(self._window.smile_worker_progress)

        self.stop_smile.connect(self._smile_worker.shutdown)

    def _setup_face_worker(self):
        self._face_worker.result.connect(self._window.update_face_recognition)
        self._face_worker.result.connect(self._smile_worker.new_recognition_result)

        self.stop_face.connect(self._face_worker.shutdown)

    def _setup_camera_worker(self):
        self._camera_worker.frame_ready.connect(self._window.update_frame)
        self._camera_worker.frame_ready.connect(self._face_worker.new_frame)
        self._camera_worker.camera_error.connect(self._window.camera_worker_error)

        self.stop_camera.connect(self._camera_worker.shutdown)

    def _create_workers(self):
        self._camera_worker = CameraWorker()
        self._face_worker = FaceDetectionWorker(SmileApp._FACE_MODEL_PATH)
        self._smile_worker = SmileDetectionWorker(SmileApp._LANDMARKER_MODEL_PATH)
        self._threads: tuple[QThread, ...] = (
            SmileApp._create_working_thread(self._camera_worker, "camera_worker"),
            SmileApp._create_working_thread(self._face_worker, "face_worker"),
            SmileApp._create_working_thread(self._smile_worker, "smile_worker"),
        )

        self._window = MainWindow()

    @staticmethod
    def _create_working_thread(worker: QObject, name: str) -> QThread:
        th = QThread(QThread.currentThread())
        th.setObjectName(name)
        th.started.connect(worker.wakeup)
        th.finished.connect(worker.deleteLater)
        worker.moveToThread(th)
        return th
