import logging
import traceback
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from smile.utils.latest_value_mailbox import LatestValueMailbox

logger = logging.getLogger(__name__)


class MailboxWorker(QObject):
    """Common single-slot mailbox loop for realtime detection workers.

    Subclasses implement ``_init_worker()`` (runs on thread start) and
    ``_process(data)`` (one item per loop iteration). Everything else —
    wakeup/shutdown, latest-wins enqueue, error reporting and the
    continue-while-pending loop — lives here.
    """

    error = Signal(type(BaseException), BaseException, str)

    def __init__(self) -> None:
        super().__init__()
        self._mailbox = LatestValueMailbox[Any]()
        thread_name: str = QThread.currentThread().objectName()
        logger.info(f'Created on thread "{thread_name}"')

    @Slot()
    def wakeup(self) -> None:
        thread_name: str = QThread.currentThread().objectName()
        logger.info(f'Waking up on thread "{thread_name}"')

        try:
            self._init_worker()
            self._mailbox.wakeup()
        except Exception as e:
            self.error.emit(type(e), e, traceback.format_exc())
            logger.error(f"Init failed: {e}")
            return

        logger.info("Started")

    def _init_worker(self) -> None:
        raise NotImplementedError

    def _cleanup(self) -> None:
        assert not self._mailbox.busy

    @Slot()
    def shutdown(self) -> None:
        self._mailbox.shutdown()
        self._cleanup()
        logger.info("Stopped")

    def _enqueue(self, data: Any) -> None:
        self._mailbox.new_data(data)

        if self._mailbox.try_start():
            QTimer.singleShot(0, self._process_next)

    @Slot()
    def _process_next(self) -> None:
        data = self._mailbox.extract_data()

        assert data is not None

        try:
            self._process(data)
        except BaseException as e:
            exctype: type = type(e)
            tb: str = traceback.format_exc()
            self.error.emit(exctype, e, tb)
            logger.error(f"Processing failed: {e}\n{tb}")
        finally:
            if self._mailbox.complete_and_should_continue():
                QTimer.singleShot(0, self._process_next)

    def _process(self, data: Any) -> None:
        raise NotImplementedError
