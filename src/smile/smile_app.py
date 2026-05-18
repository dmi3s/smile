from PySide6.QtWidgets import QApplication

from smile.windows.main_window import MainWindow


class SmileApp(QApplication):
    def __init__(self, args: list[str]) -> None:
        super().__init__(args)
        self.window = MainWindow()
        self.window.show()
