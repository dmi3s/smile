import numpy as np

from smile.camera.frame import Frame
from smile.recognition.detectors.face_detection import (
    DetectedFaceBox,
    FaceBox,
    FaceDetectionResult,
)
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
        FaceDetectionResult(faces=faces, small_frame_rgb=_frame(0, 1_000_000_000), frame_id=0)
    )

    window.update_frame(_frame(1, 1_050_000_000))

    label = window.ui.video_label
    assert label._image is not None
    assert label._image.size().width() == 800
    assert len(label._face_boxes) == 2

    for i in range(3):
        window.update_frame(_frame(2 + i, 1_050_000_000 + (2 + i) * 10_000_000))

    qapp.processEvents()