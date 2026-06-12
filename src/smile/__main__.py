import logging
import sys

from smile.smile_app import SmileApp


def _setup_logging(log_level: int | str | None) -> None:
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)-8s] [%(thread)X] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),  # В консоль
            # logging.FileHandler(f"logs/smile-{dt.today()}.log"),  # В файл
        ],
    )


def main() -> None:
    _setup_logging(logging.INFO)

    app = SmileApp(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
