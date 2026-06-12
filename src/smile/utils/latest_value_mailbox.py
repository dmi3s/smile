from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LatestValueMailbox[T]:
    """
    Single-slot mailbox state for realtime workers.

    New data overwrites old pending data.
    Designed for realtime processing pipelines where
    latency is preferred over completeness.

    Thread affinity:
        All methods must be called from the same Qt thread.

    Remark:
        The missing "S" in SOLID here is intentional.
        Convenience won this round.
    """

    _pending_data: T | None = None
    _running: bool = False
    _busy: bool = False

    def wakeup(self) -> None:
        assert not self._running
        assert not self._busy

        self._running = True

    def shutdown(self) -> None:
        self._running = False
        self._busy = False
        self._pending_data = None

    def start_working(self) -> None:
        assert self._running
        assert not self._busy

        self._busy = True

    def stop_working(self) -> None:
        # assert self._runnign
        ## This is too strong:
        ## 1. worker.start_working()
        ## 2. shutdown()
        ## 3. _running = False
        ## 4. finally: worker.stop_working()
        ## 5. Happy debugging... you got this!

        assert self._busy

        self._busy = False

    @property
    def can_schedule(self) -> bool:
        return self._running and not self._busy and self._pending_data is not None

    def try_start(self) -> bool:
        if not self._running:
            return False

        if self._busy:
            return False

        if self._pending_data is None:
            return False

        self._busy = True
        return True

    @property
    def busy(self) -> bool:
        return self._busy

    def complete_and_should_continue(self) -> bool:
        self.stop_working()
        return self.try_start()

    def new_data(self, data: T) -> None:
        assert self._running

        self._pending_data = data

    @property
    def has_pending_data(self) -> bool:
        return self._pending_data is not None

    def extract_data(self) -> T | None:
        # assert self._running
        ## Enable extracting data after shutdown.
        ## Just in case.

        data: T | None = self._pending_data
        self._pending_data = None

        return data

    @contextmanager
    def work(self) -> Generator[None, Any, None]:
        self.start_working()
        try:
            yield
        finally:
            self.stop_working()

    @contextmanager
    def active(self) -> Generator[None, Any, None]:
        try:
            yield
        finally:
            self.stop_working()
