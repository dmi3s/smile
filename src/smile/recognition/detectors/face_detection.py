from dataclasses import dataclass

from numpy import ndarray

from smile.camera.frame import Frame


@dataclass(slots=True, frozen=True)
class FaceBox:
    fx: float
    fy: float
    fw: float
    fh: float


@dataclass(slots=True, frozen=True)
class DetectedFaceBox:
    bbox: FaceBox
    score: float


@dataclass(slots=True, frozen=True)
class FaceDetectionResult:
    faces: tuple[DetectedFaceBox, ...]
    small_frame_rgb: Frame
