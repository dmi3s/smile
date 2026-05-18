import logging
import sys
from datetime import datetime as dt

from smile.smile_app import SmileApp


def _setup_logging(logLevel: int | str | None) -> None:
    logging.basicConfig(
        level=logLevel,
        format="%(asctime)s [%(levelname)-8s] [%(thread)X] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),  # В консоль
            logging.FileHandler(f"smile-{dt.today()}.log"),  # В файл
        ],
    )


def main() -> None:
    _setup_logging(logging.INFO)

    app = SmileApp(sys.argv)
    sys.exit(app.exec())
