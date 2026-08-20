import time
from typing import Any

import cv2
import numpy as np
import pytest
from PySide6.QtCore import QThread
from PySide6.QtTest import QTest

from smile.camera.camera_worker import CameraWorker


class _FakeCapture:
    """Minimal stand-in for cv2.VideoCapture driven by a shared `state` dict."""

    def __init__(self, state: dict[str, bool]) -> None:
        self._state = state
        self._props: dict[int, float] = {}
        self.released = False

    def isOpened(self) -> bool:
        return self._state["opened"]

    def set(self, prop: int, value: float) -> None:
        self._props[prop] = value

    def get(self, prop: int) -> float:
        return self._props.get(prop, 0.0)

    def getBackendName(self) -> str:
        return "fake"

    def read(self) -> tuple[bool, Any]:
        if not self._state["opened"] or not self._state["read_ok"]:
            return False, None
        return True, np.zeros((448, 800, 3), dtype=np.uint8)

    def release(self) -> None:
        self.released = True


def _wait_until(cond, timeout_ms: int = 3000) -> None:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        QTest.qWait(10)
        if cond():
            return
    raise AssertionError("condition not met within timeout")


@pytest.mark.parametrize(
    "startup_failure",
    [False, True],
    ids=["runtime-failure", "startup-failure"],
)
def test_camera_reconnect(qapp, monkeypatch, startup_failure: bool) -> None:
    state = {"opened": not startup_failure, "read_ok": True}

    monkeypatch.setattr(cv2, "VideoCapture", lambda _source: _FakeCapture(state))
    monkeypatch.setattr(CameraWorker, "RETRY_DELAY_MS", 20)
    monkeypatch.setattr(CameraWorker, "FRAME_FPS", 100)
    monkeypatch.setattr(CameraWorker, "_video_device_paths", lambda _self: [])

    worker = CameraWorker()
    th = QThread()
    th.setObjectName("camera_test")
    th.started.connect(worker.wakeup)
    worker.moveToThread(th)

    frame_ids: list[int] = []
    errors: list[str] = []
    recovered: list[bool] = []

    worker.frame_ready.connect(lambda frame: frame_ids.append(frame.frame_id))
    worker.camera_error.connect(errors.append)
    worker.camera_recovered.connect(lambda: recovered.append(True))

    th.start()
    try:
        if startup_failure:
            _wait_until(lambda: len(errors) >= 1)
            assert errors == ["Cannot open any camera"]
        else:
            _wait_until(lambda: len(frame_ids) >= 3)
            assert len(frame_ids) >= 3

        # The camera dies at runtime: next read() fails.
        if not startup_failure:
            state["read_ok"] = False
            _wait_until(lambda: len(errors) >= 1)
            assert errors == ["Failed to read frame"]
            frames_while_dead = len(frame_ids)
            QTest.qWait(100)
            assert len(frame_ids) == frames_while_dead  # no frames while dead

        # Camera still unavailable: every open attempt fails, no error spam.
        state["opened"] = False
        QTest.qWait(100)
        assert len(errors) == 1

        # Camera reappears: reconnect succeeds and frames flow again.
        state["opened"] = True
        state["read_ok"] = True
        _wait_until(lambda: len(recovered) >= 1 and len(frame_ids) > 0)
        assert recovered == [True]
        assert len(frame_ids) > 0
    finally:
        worker.shutdown()
        th.quit()
        assert th.wait(2000)
