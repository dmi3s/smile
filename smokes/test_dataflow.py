import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap

from smile.camera.frame import Frame


def _make_frame() -> Frame:
    rng = np.random.default_rng(42)
    raw = rng.integers(0, 256, (448, 800, 3), dtype=np.uint8)
    raw.flags.writeable = False
    return Frame.create_share(raw, 0, 1)


def test_share_does_not_copy():
    frame = _make_frame()
    assert frame.image.flags.writeable is False
    assert frame.image is frame.image  # share keeps the same buffer


def test_share_buffers_survive_consumer_path(qapp):
    frame = _make_frame()
    original = frame.image

    small = cv2.resize(
        frame.image, dsize=(0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA
    )
    rgb = np.ascontiguousarray(small[:, :, ::-1])
    rgb.flags.writeable = False

    assert rgb.shape == (224, 400, 3)
    assert rgb.flags.contiguous

    w, h, ch = frame.image.shape[1], frame.image.shape[0], frame.image.shape[2]
    qimage = QImage(frame.image.data, w, h, ch * w, QImage.Format.Format_BGR888)
    assert qimage.size().width() == w

    pixmap = QPixmap.fromImage(qimage)
    assert pixmap.size().width() == w
    assert not pixmap.isNull()

    # consumers must not mutate the shared buffer
    assert frame.image is original
    assert frame.image.flags.writeable is False
