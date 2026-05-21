from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

import math as m

from PySide6.QtCore import QRect

T = TypeVar('T')
BlendFunc = Callable[[T, T, float], T]  # signature: (old, new, alpha) -> blended

class ExponentialJitterSmoother[T]:
    def __init__(self, alpha: float, blend_func: BlendFunc[T] | None = None):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self._blend = blend_func
        self._state: T | None = None

    def update(self, value: T) -> T:
        if self._state is None:
            self._state = value
            return self._state

        if self._blend:
            self._state = self._blend(self._state, value, self.alpha)
        else:
            # Fallback для числовых типов (float, int)
            self._state = self._state * (1.0 - self.alpha) + value * self.alpha  # ty:ignore[unsupported-operator]
        return self._state

    def reset(self) -> None:
        self._state = None

    @property
    def is_initialized(self) -> bool:
        return self._state is not None

def blend_qrect(old: QRect, new: QRect, alpha: float) -> QRect:
    x = m.floor(old.x() * (1.0 - alpha) + new.x() * alpha)
    y = m.floor(old.y() * (1.0 - alpha) + new.y() * alpha)
    # Not sure about width
    w = m.floor(old.width() * (1.0 - alpha) + new.width() * alpha)
    h = m.floor(old.height() * (1.0 - alpha) + new.height() * alpha)
    return QRect(x, y, w, h)


FloatSmoother = ExponentialJitterSmoother[float]
QRectSmoother = ExponentialJitterSmoother[QRect]
'''
    bbox_smoother = QRectSmoother(alpha = 0.25, blend_func = blend_qrect)
    smooth_rect = bbox_smoother.update(raw_rect)
'''

