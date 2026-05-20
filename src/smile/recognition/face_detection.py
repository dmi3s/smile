from dataclasses import dataclass


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
class RecognitionResult:
    faces: list[DetectedFaceBox]
    timestamp_ns: int
    frame_id: int
