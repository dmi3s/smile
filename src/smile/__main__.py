import logging
import sys
from datetime import date
from pathlib import Path

from smile.smile_app import SmileApp


def _setup_logging(log_level: int | str | None) -> None:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)-8s] [%(thread)X] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),  # В консоль
            logging.FileHandler(log_dir / f"smile-{date.today()}.log"),  # В файл
        ],
    )


def main() -> None:
    _setup_logging(logging.INFO)

    app = SmileApp(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
