from dataclasses import dataclass

from mediapipe.tasks.python import vision


@dataclass(slots=True, frozen=True)
class RecognitionResult:
    # It's a compromise
    result: vision.FaceDetectorResult
    timestamp_ns: int
    frame_id: int
