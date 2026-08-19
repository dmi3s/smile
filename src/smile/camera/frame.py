from dataclasses import dataclass

import numpy as np


@dataclass(slots=True, frozen=True)
class Frame:
    image: np.ndarray
    frame_id: int
    timestamp_ns: int

    @classmethod
    def create_share(cls, image: np.ndarray, frame_id: int, timestamp_ns: int):
        image.flags.writeable = False
        return cls(image, frame_id, timestamp_ns)

    @classmethod
    def create_copy(cls, image: np.ndarray, frame_id: int, timestamp_ns: int):
        snapshot = image.copy()
        snapshot.flags.writeable = False
        return cls(snapshot, frame_id, timestamp_ns)
