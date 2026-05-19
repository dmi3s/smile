from dataclasses import dataclass

import numpy as np


@dataclass(slots=True, frozen=True)
class Frame:
    image: np.ndarray
    frame_id: int
    timestamp_ns: int

    @classmethod
    def from_owned(cls, image: np.ndarray, frame_id: int, timestamp_ns: int):
        return cls(image, frame_id, timestamp_ns)

    @classmethod
    def from_copy(cls, image: np.ndarray, frame_id: int, timestamp_ns: int):
        return cls(image.copy(), frame_id, timestamp_ns)
