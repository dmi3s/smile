import logging

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import QApplication

from smile.camera.camera_worker import CameraWorker
from smile.recognition.recognition_worker import RecognitionWorker
from smile.windows.main_window import MainWindow

logger = logging.getLogger(__name__)


class SmileApp(QApplication):
    stop_camera = Signal()
    stop_recognition = Signal()

    def __init__(self, args: list[str]):
        super().__init__(args)

        logger.info("Application creating")

        self.camera_worker = CameraWorker()
        self.camera_thread = QThread()
        self.camera_worker.moveToThread(self.camera_thread)

        self.recognition_worker = RecognitionWorker()
        self.recognition_thread = QThread()
        self.recognition_worker.moveToThread(self.recognition_thread)

        self.window = MainWindow()

        self.camera_thread.started.connect(self.camera_worker.start)
        self.camera_worker.frame_ready.connect(self.recognition_worker.process_frame)
        self.stop_camera.connect(self.camera_worker.stop)

        self.recognition_thread.started.connect(self.recognition_worker.start)
        self.recognition_worker.qimage_ready.connect(self.window.update_qimage)
        self.stop_recognition.connect(self.recognition_worker.stop)

        self.camera_thread.finished.connect(self.camera_worker.deleteLater)
        self.recognition_thread.finished.connect(self.recognition_worker.deleteLater)

        self.aboutToQuit.connect(self.shutdown)

        self.window.show()

        self.recognition_thread.start()
        self.camera_thread.start()

        logger.info("Application created")

    @Slot()
    def shutdown(self) -> None:
        logger.info("Application shutdown started")

        self.stop_camera.emit()
        self.stop_recognition.emit()

        self.camera_thread.quit()
        self.recognition_thread.quit()

        self.camera_thread.wait()
        self.recognition_thread.wait()

        logger.info("Application shutdown completed")
