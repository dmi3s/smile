from dataclasses import dataclass

import numpy as np


@dataclass(slots=True, frozen=True)
class Frame:
    image: np.ndarray
    frame_id: int
    timestamp: float

    @classmethod
    def from_shared(cls, image: np.ndarray, frame_id: int, timestamp: float):
        return cls(image, frame_id, timestamp)

    @classmethod
    def from_copy(cls, image: np.ndarray, frame_id: int, timestamp: float):
        return cls(image.copy(), frame_id, timestamp)
