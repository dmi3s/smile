import numpy as np

from smile.camera.frame import Frame
from smile.recognition.detectors.face_detection import (
    DetectedFaceBox,
    FaceBox,
    FaceDetectionResult,
)
from smile.recognition.detectors.flashlight_detection import FlashlightDetectionResult
from smile.recognition.detectors.smile_detection import SmileDetectionResult
from smile.windows import main_window
from smile.windows.main_window import MainWindow


def _frame(frame_id: int, ts_ns: int) -> Frame:
    rng = np.random.default_rng(3)
    img = rng.integers(0, 256, (448, 800, 3), dtype=np.uint8)
    img.flags.writeable = False
    return Frame.create_share(img, frame_id, ts_ns)


def test_update_frame_pipeline(qapp):
    window = MainWindow()
    window.show()

    window.update_frame(_frame(0, 1_000_000_000))

    faces = (
        DetectedFaceBox(bbox=FaceBox(0.1, 0.2, 0.3, 0.4), score=0.95),
        DetectedFaceBox(bbox=FaceBox(0.5, 0.3, 0.2, 0.3), score=0.6),
    )
    window.update_face_recognition(
        FaceDetectionResult(
            faces=faces, small_frame_rgb=_frame(0, 1_000_000_000), frame_id=0
        )
    )

    window.update_frame(_frame(1, 1_050_000_000))

    label = window.ui.video_label
    assert label.image is not None
    assert label.image.size().width() == 800
    assert len(label.face_boxes) == 2

    for i in range(3):
        window.update_frame(_frame(2 + i, 1_050_000_000 + (2 + i) * 10_000_000))

    qapp.processEvents()


def test_smile_status_updates_emoji(qapp):
    window = MainWindow()
    window.show()

    window.update_smile_status(SmileDetectionResult(smile_scores=(), frame_id=0))
    assert window.ui.smile_label.text() == "🖖"

    for i in range(5):
        window.update_smile_status(
            SmileDetectionResult(smile_scores=(0.0,), frame_id=1 + i)
        )
    assert window.ui.smile_label.text() == "😐"

    for i in range(10):
        window.update_smile_status(
            SmileDetectionResult(smile_scores=(0.4,), frame_id=10 + i)
        )
    assert window.ui.smile_label.text() == "😊"

    for i in range(10):
        window.update_smile_status(
            SmileDetectionResult(smile_scores=(0.8,), frame_id=20 + i)
        )
    assert window.ui.smile_label.text() == "😄"


def test_smile_status_smoothing_holds_then_decays(qapp):
    window = MainWindow()
    window.show()

    window.update_smile_status(SmileDetectionResult(smile_scores=(0.9,), frame_id=1))
    assert window.ui.smile_label.text() == "😄"

    # a single neutral frame must not flicker the emoji back
    window.update_smile_status(SmileDetectionResult(smile_scores=(0.0,), frame_id=2))
    assert window.ui.smile_label.text() == "😄"

    # sustained neutral frames decay the smoothed score below the threshold
    for i in range(10):
        window.update_smile_status(
            SmileDetectionResult(smile_scores=(0.0,), frame_id=3 + i)
        )
    assert window.ui.smile_label.text() == "😐"


def test_smile_status_resets_on_no_face(qapp):
    window = MainWindow()
    window.show()

    for i in range(5):
        window.update_smile_status(
            SmileDetectionResult(smile_scores=(0.8,), frame_id=1 + i)
        )
    assert window.ui.smile_label.text() == "😄"

    # face lost -> smoother resets, emoji goes back to no-face state immediately
    window.update_smile_status(SmileDetectionResult(smile_scores=(), frame_id=6))
    assert window.ui.smile_label.text() == "🖖"


def test_screenshot_saves_to_smile_dir(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(main_window, "SCREENSHOT_DIR", tmp_path)
    window = MainWindow()
    window.show()
    window.update_frame(_frame(0, 1_000_000_000))

    window._take_screenshot()

    files = list(tmp_path.glob("smile-*.png"))
    assert len(files) == 1
    assert files[0].stat().st_size > 0


def test_statusbar_shows_smile_and_fps(qapp):
    window = MainWindow()
    window.show()

    for i in range(5):
        window.update_frame(_frame(i, 1_000_000_000 + i * 50_000_000))

    window.update_face_recognition(
        FaceDetectionResult(faces=(), small_frame_rgb=None, frame_id=0)
    )
    window.update_smile_status(SmileDetectionResult(smile_scores=(0.8,), frame_id=1))

    text = window.ui.statusbar.currentMessage()
    assert "smile=0.80" in text
    assert "cam 20" in text
    assert "fps" in text


def test_flashlight_status_and_overlay(qapp):
    window = MainWindow()
    window.show()

    window.update_flashlight(
        FlashlightDetectionResult(
            detected=True,
            score=0.9,
            bright_bbox=FaceBox(0.3, 0.4, 0.2, 0.3),
            brightness=1.0,
            frame_id=1,
        )
    )

    assert "🔦 0.90" in window.ui.statusbar.currentMessage()

    window.update_frame(_frame(2, 1_050_000_000))
    assert window.ui.video_label.flashlight_bbox == FaceBox(0.3, 0.4, 0.2, 0.3)

    window.update_flashlight(
        FlashlightDetectionResult(
            detected=False,
            score=0.0,
            bright_bbox=None,
            brightness=0.0,
            frame_id=3,
        )
    )
    assert "🔦 —" in window.ui.statusbar.currentMessage()
    window.update_frame(_frame(4, 1_100_000_000))
    assert window.ui.video_label.flashlight_bbox is None
