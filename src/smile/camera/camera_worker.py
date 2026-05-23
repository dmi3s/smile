import logging
import time

import cv2
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from smile.camera.frame import Frame

logger = logging.getLogger(__name__)


class CameraWorker(QObject):
    frame_ready = Signal(Frame)
    camera_error = Signal(str)
    camera_started = Signal()
    # ToDo:
    # stop_camera = Signal()
    # fps_updated = Signal()
    # camera_disconnected = Signal()

    def __init__(self):
        super().__init__()
        self._frame_count = 0
        self._timer : QTimer = QTimer(self)
        self._timer.timeout.connect(self._capture_frame)
        self._cap : cv2.VideoCapture | None = None
        self._stopping = False
        thread_name : str = QThread.currentThread().objectName()
        logger.info(f"Created on thread \"{thread_name}\"")

    @Slot()
    def wakeup(self) -> None:
        thread_name : str = QThread.currentThread().objectName()
        logger.info(f"Waking up on thread \"{thread_name}\"")

        self._cap = cv2.VideoCapture(0)

        assert self._cap is not None

        if not self._cap.isOpened():
            logger.error("Cannot open default camera")
            self.camera_error.emit("Cannot open default camera")
            return

        self._setup_camera()

        self.camera_started.emit()

        logger.info("Started")

    def _setup_camera(self):
        assert self._cap is not None
        assert self._cap.isOpened()

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 448)
        self._cap.set(cv2.CAP_PROP_FPS, 20)
        fps : int = int(self._cap.get(cv2.CAP_PROP_FPS))

        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        backend: str = self._cap.getBackendName()
        logger.info(f"Camera mode: {w}x{h} @ {fps} ({backend=})")

        assert 0 < fps <= 1000
        self._timer.start(1000 // fps)



    @Slot()
    def _capture_frame(self) -> None:
        if self._stopping:
            return
        assert self._cap is not None

        ret, bgr_frame = self._cap.read()

        if not ret:
            logger.warning("Failed to read frame")
            self.camera_error.emit("Failed to read frame")
            return

        timestamp_ns = time.monotonic_ns()
        # rgb_image = cast(
        #     NDArray,
        #     cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        # )
        # or
        # rgb_image = np.ascontiguousarray(bgr_frame[:, :, ::-1])

        frame = Frame.create_copy(bgr_frame, self._frame_count, timestamp_ns)
        bgr_frame.flags.writeable = False

        self._frame_count += 1

        self.frame_ready.emit(frame)

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
