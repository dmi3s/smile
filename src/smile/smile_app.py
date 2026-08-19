from __future__ import annotations

import logging
import signal
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication

from smile.camera.camera_worker import CameraWorker
from smile.recognition.detectors.face_detection_worker import FaceDetectionWorker
from smile.recognition.detectors.flashlight_detection_worker import (
    FlashlightDetectionWorker,
)
from smile.recognition.detectors.smile_detection_worker import SmileDetectionWorker
from smile.windows.main_window import MainWindow

logger = logging.getLogger(__name__)


if TYPE_CHECKING:

    class _Worker(Protocol):
        def wakeup(self) -> None: ...


class SmileApp(QApplication):
    stop_camera = Signal()
    stop_face = Signal()
    stop_smile = Signal()
    stop_flashlight = Signal()

    _FACE_MODEL_PATH = (
        Path(__file__).resolve().parent
        / "recognition"
        / "models"
        / "blaze_face_short_range.tflite"
    )

    _LANDMARKER_MODEL_PATH = (
        Path(__file__).resolve().parent
        / "recognition"
        / "models"
        / "face_landmarker.task"
    )

    _FLASHLIGHT_MODEL_PATH = (
        Path(__file__).resolve().parent
        / "recognition"
        / "models"
        / "mobilenet_v2_1.0_224.tflite"
    )

    def __init__(self, args: list[str]):
        super().__init__(args)

        logger.info("Initializing ...")

        self._shutdown_started = False

        self._create_workers()

        self._setup_camera_worker()
        self._setup_face_worker()
        self._setup_smile_worker()
        self._setup_flashlight_worker()

        self.aboutToQuit.connect(self.shutdown)

        # Exit cleanly on SIGINT/SIGTERM (e.g. kill, service stop, terminal
        # close) instead of leaving the process hanging without a terminal.
        signal.signal(signal.SIGINT, self._quit_on_signal)
        signal.signal(signal.SIGTERM, self._quit_on_signal)

        # Let's go
        self._window.show()

        for th in self._threads:
            th.start()

        logger.info("Initialization completed")

    def _quit_on_signal(self, signum: int, _frame: object) -> None:
        logger.warning(f"Received signal {signum}, shutting down")
        self.quit()

    @Slot()
    def shutdown(self) -> None:
        if self._shutdown_started:
            logger.debug("shutdown already in progress, skipping")
            return
        self._shutdown_started = True

        logger.info("Shutting down ...")

        self.stop_camera.emit()
        self.stop_face.emit()
        self.stop_smile.emit()
        self.stop_flashlight.emit()

        for th in self._threads:
            th.quit()

        for th in self._threads:
            if not th.wait(3000):
                logger.warning(f'Thread "{th.objectName()}" did not stop.')

        logger.info("Shutdown completed")

    def _setup_smile_worker(self):
        self._smile_worker.result.connect(self._window.update_smile_status)
        self._smile_worker.error.connect(self._window.smile_worker_error)
        self._smile_worker.progress.connect(self._window.smile_worker_progress)

        self.stop_smile.connect(self._smile_worker.shutdown)

    def _setup_face_worker(self):
        self._face_worker.result.connect(self._window.update_face_recognition)
        self._face_worker.result.connect(self._smile_worker.new_face_detection_result)

        self.stop_face.connect(self._face_worker.shutdown)

    def _setup_flashlight_worker(self):
        self._flashlight_worker.result.connect(self._window.update_flashlight)
        self._flashlight_worker.error.connect(self._window.flashlight_worker_error)
        self._flashlight_worker.progress.connect(
            self._window.flashlight_worker_progress
        )

        self.stop_flashlight.connect(self._flashlight_worker.shutdown)

    def _setup_camera_worker(self):
        self._camera_worker.frame_ready.connect(self._window.update_frame)
        self._camera_worker.frame_ready.connect(self._face_worker.new_frame)
        self._camera_worker.frame_ready.connect(self._flashlight_worker.new_frame)
        self._camera_worker.camera_error.connect(self._window.camera_worker_error)

        self.stop_camera.connect(self._camera_worker.shutdown)

    def _create_workers(self):
        self._camera_worker = CameraWorker()
        self._face_worker = FaceDetectionWorker(SmileApp._FACE_MODEL_PATH)
        self._smile_worker = SmileDetectionWorker(SmileApp._LANDMARKER_MODEL_PATH)
        self._flashlight_worker = FlashlightDetectionWorker(
            SmileApp._FLASHLIGHT_MODEL_PATH
        )
        self._threads: tuple[QThread, ...] = (
            SmileApp._create_working_thread(self._camera_worker, "camera_worker"),
            SmileApp._create_working_thread(self._face_worker, "face_worker"),
            SmileApp._create_working_thread(self._smile_worker, "smile_worker"),
            SmileApp._create_working_thread(
                self._flashlight_worker, "flashlight_worker"
            ),
        )

        self._window = MainWindow()

    @staticmethod
    def _create_working_thread(worker: _Worker, name: str) -> QThread:
        th = QThread(QThread.currentThread())
        th.setObjectName(name)
        th.started.connect(worker.wakeup)
        th.finished.connect(cast(QObject, worker).deleteLater)
        cast(QObject, worker).moveToThread(th)
        return th
