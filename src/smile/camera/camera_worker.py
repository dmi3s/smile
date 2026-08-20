import glob
import logging
import sys
import time

import cv2
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from smile.camera.frame import Frame

logger = logging.getLogger(__name__)


class CameraWorker(QObject):
    CAMERA_INDEX: int = 0
    MAX_CAMERA_INDEX: int = 6
    FRAME_WIDTH: int = 800
    FRAME_HEIGHT: int = 448
    FRAME_FPS: int = 20
    RETRY_DELAY_MS: int = 2000
    PROBE_READ_ATTEMPTS: int = 10
    PROBE_READ_DELAY_S: float = 0.03

    frame_ready = Signal(Frame)
    camera_error = Signal(str)
    camera_recovered = Signal()

    def __init__(self):
        super().__init__()
        self._frame_count = 0
        self._timer: QTimer | None = QTimer(self)
        self._timer.timeout.connect(self._capture_frame)
        self._cap: cv2.VideoCapture | None = None
        self._stopping = False
        self._reconnecting = False
        self._last_source: int | str | None = None
        thread_name: str = QThread.currentThread().objectName()
        logger.info(f'Created on thread "{thread_name}"')

    @Slot()
    def wakeup(self) -> None:
        thread_name: str = QThread.currentThread().objectName()
        logger.info(f'Waking up on thread "{thread_name}"')

        if not self._open_camera():
            self.camera_error.emit("Cannot open any camera")
            self._schedule_retry()
            return

        logger.info("Started")

    def _open_camera(self) -> bool:
        # Мы вынуждены делать так, т.к. должны работать, спасибо за рыбу %)
        # V4L2 по индексу держит «мёртвый» дескриптор после отключения USB-камеры
        # (свежий процесс находит её, а этот — нет), индекс может смениться,
        # а открытие по пути /dev/videoN идёт через FFMPEG и переживает replug.
        for source in self._camera_sources():
            cap = self._try_open(source)
            if cap is not None:
                self._cap = cap
                self._last_source = source
                logger.info(f"Camera opened from source: {source}")
                self._setup_camera()
                return True
        return False

    def _camera_sources(self) -> list[int | str]:
        """Candidate sources, most recently used first."""
        sources: list[int | str] = []
        if self._last_source is not None:
            sources.append(self._last_source)
        sources.extend(range(CameraWorker.MAX_CAMERA_INDEX))
        sources.extend(self._video_device_paths())

        seen: set[int | str] = set()
        result: list[int | str] = []
        for source in sources:
            if source not in seen:
                seen.add(source)
                result.append(source)
        return result

    def _video_device_paths(self) -> list[str]:
        if not sys.platform.startswith("linux"):
            return []
        return sorted(glob.glob("/dev/video*"))

    def _try_open(self, source: int | str) -> cv2.VideoCapture | None:
        cap = cv2.VideoCapture(source)
        if cap is None or not cap.isOpened():
            if cap is not None:
                cap.release()
            return None
        if self._probe_capture(cap):
            return cap
        logger.warning(f"Source {source} opened but produced no frame, skipping")
        cap.release()
        return None

    def _probe_capture(self, cap: cv2.VideoCapture) -> bool:
        for _ in range(CameraWorker.PROBE_READ_ATTEMPTS):
            ret, frame = cap.read()
            if ret and frame is not None and frame.ndim == 3:
                return True
            time.sleep(CameraWorker.PROBE_READ_DELAY_S)
        return False

    def _schedule_retry(self) -> None:
        if self._stopping:
            return
        if self._reconnecting:
            return
        self._reconnecting = True
        QTimer.singleShot(CameraWorker.RETRY_DELAY_MS, self._retry)

    @Slot()
    def _retry(self) -> None:
        self._reconnecting = False
        if self._stopping:
            return

        if self._open_camera():
            self._frame_count = 0
            self.camera_recovered.emit()
            logger.info("Camera reconnected")
            return

        logger.warning("Camera still unavailable, retrying ...")
        self._schedule_retry()

    def _setup_camera(self) -> None:
        if self._cap is None:
            logger.error("Camera capture is not initialized")
            return
        if not self._cap.isOpened():
            logger.error("Camera is not opened")
            return

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, CameraWorker.FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CameraWorker.FRAME_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, CameraWorker.FRAME_FPS)
        fps: int = int(self._cap.get(cv2.CAP_PROP_FPS))

        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        backend: str = self._cap.getBackendName()
        logger.info(f"Camera mode: {w}x{h} @ {fps} ({backend=})")

        if not 0 < fps <= 1000:
            logger.warning(
                f"Invalid camera FPS: {fps}; falling back to {CameraWorker.FRAME_FPS}"
            )
            fps = CameraWorker.FRAME_FPS

        if self._timer is None:
            logger.error("Timer is not initialized")
            return

        self._timer.start(1000 // fps)

    @Slot()
    def _capture_frame(self) -> None:
        if self._stopping:
            return
        if self._cap is None:
            return

        ret, bgr_frame = self._cap.read()

        if not ret:
            logger.warning("Failed to read frame")
            self.camera_error.emit("Failed to read frame")
            self._enter_reconnect()
            return

        timestamp_ns = time.monotonic_ns()

        # Copy once at the source: the Frame owns a private read-only snapshot,
        # so the GUI (QImage) and the CV workers never read a half-overwritten
        # buffer.
        frame = Frame.create_copy(bgr_frame, self._frame_count, timestamp_ns)

        self._frame_count += 1

        self.frame_ready.emit(frame)

    def _enter_reconnect(self) -> None:
        if self._reconnecting:
            return
        if self._timer is not None:
            self._timer.stop()
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._schedule_retry()

    @Slot()
    def shutdown(self) -> None:
        self._stopping = True
        self._frame_count = 0

        if self._timer is not None:
            self._timer.stop()
            self._timer = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

        logger.info("Stopped")
