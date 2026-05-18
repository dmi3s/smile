from PySide6.QtCore import Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QMainWindow

from smile.ui.generated.ui_main_window import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

    @Slot(QImage)
    def update_pixmap(self, qimage: QImage) -> None:
        pixmap = QPixmap.fromImage(qimage)
        self.ui.video_label.setPixmap(pixmap)
