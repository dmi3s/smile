import time


class FpsMeter:
    """Smoothed frames-per-second measured from arrival timestamps.

    Pure logic, no Qt. Call ``update()`` on every arrival; the returned value
    is an exponential moving average of the instantaneous frame rate.
    """

    def __init__(self, alpha: float = 0.1) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self._alpha = alpha
        self._prev_ts_ns: int = 0
        self._fps: float = 0.0

    def update(self, ts_ns: int | None = None) -> float:
        if ts_ns is None:
            ts_ns = time.monotonic_ns()
        if self._prev_ts_ns:
            delta = ts_ns - self._prev_ts_ns
            if delta > 0:
                instant = 1e9 / delta
                self._fps = (
                    instant
                    if self._fps == 0.0
                    else self._fps * (1.0 - self._alpha) + instant * self._alpha
                )
        self._prev_ts_ns = ts_ns
        return self._fps

    @property
    def fps(self) -> float:
        return self._fps

    def reset(self) -> None:
        self._prev_ts_ns = 0
        self._fps = 0.0
