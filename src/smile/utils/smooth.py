# mypy: ignore-errors

from collections.abc import Callable


class ExponentialJitterSmoother:
    def __init__(self, alpha: float, blend_func: Callable = None):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self._blend = blend_func
        self._state = None

    def update(self, value):
        if self._state is None:
            self._state = value
            return self._state
        if self._blend:
            self._state = self._blend(self._state, value, self.alpha)
        else:
            self._state = self._state * (1.0 - self.alpha) + value * self.alpha
        return self._state

    def reset(self):
        self._state = None

    @property
    def is_initialized(self):
        return self._state is not None


# Для совместимости с кодом, который ожидает FloatSmoother = ExponentialJitterSmoother[float]
FloatSmoother = ExponentialJitterSmoother
