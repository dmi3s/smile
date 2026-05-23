from dataclasses import dataclass

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
    frame_bgr: Frame | None
