import gc

import numpy as np
from PySide6.QtCore import QRect, QSize
from PySide6.QtGui import QImage

from smile.recognition.detectors.face_detection import DetectedFaceBox, FaceBox
from smile.widgets.overlay_label import OverlayLabel

FACES = (DetectedFaceBox(bbox=FaceBox(0.25, 0.25, 0.5, 0.5), score=0.9),)


def _image(shape: tuple[int, int, int], seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = rng.integers(0, 256, shape, dtype=np.uint8)
    img.flags.writeable = False
    return img


def test_draw_rect_math(qapp):
    label = OverlayLabel()
    label.resize(640, 480)
    label.set_frame(_image((448, 800, 3), 7), FACES, 1_000_000_000, True)
    # 800x448 -> fit 640x480: scale 0.8 -> 640x358, y-offset 61
    assert label._draw_rect() == QRect(0, 61, 640, 358)


def test_map_rect_math(qapp):
    label = OverlayLabel()
    label.resize(640, 480)
    label.set_frame(_image((448, 800, 3), 7), FACES, 1_000_000_000, True)
    # image px (0,0,400,224) scaled by 0.8, offset (0,61)
    assert label._map_rect(QRect(0, 0, 400, 224)) == QRect(0, 61, 320, 179)


def test_frame_lifetime(qapp):
    label = OverlayLabel()
    img = _image((448, 800, 3), 7)
    label.set_frame(img, FACES, 1_000_000_000, True)
    expected = QSize(800, 448)
    assert label._image is not None
    assert label._image.size() == expected

    del img
    gc.collect()

    assert label._image.size() == expected


def test_render_produces_pixels(qapp):
    label = OverlayLabel()
    label.resize(640, 480)
    label.set_frame(_image((448, 800, 3), 7), FACES, 1_000_000_000, True)

    out = QImage(label.size(), QImage.Format.Format_ARGB32)
    label.render(out)
    assert not out.isNull()
    assert out.size() == label.size()


def test_frame_replacement(qapp):
    label = OverlayLabel()
    label.set_frame(_image((448, 800, 3), 7), FACES, 1_000_000_000, True)
    label.set_frame(_image((224, 400, 3), 8), FACES, 2_000_000_000, True)
    assert label._image is not None
    assert label._image.size() == QSize(400, 224)
