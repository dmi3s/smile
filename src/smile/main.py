import sys

from smile.smile_app import SmileApp


def main() -> None:
    app = SmileApp(sys.argv)
    sys.exit(app.exec())
