from PySide6.QtCore import Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QMainWindow

from smile.camera.frame import Frame
from smile.recognition.face_detection import RecognitionResult
from smile.ui.generated.ui_main_window import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

    @Slot(Frame)
    def update_frame(self, frame: Frame) -> None:
        image = frame.image
        height, width, channels = image.shape
        # logger.info(f"Frame {frame.frame_id} {width} x {height} x {channels}")
        bytes_per_line = channels * width

        qimage = QImage(
            image.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )

        pixmap = QPixmap.fromImage(qimage)
        self.ui.video_label.setPixmap(pixmap)

    @Slot(RecognitionResult)
    def update_detection(self, detection_result: RecognitionResult) -> None:
        if len(detection_result.result.detections) > 0:
            self.ui.smile_label.setText("🙂")
        else:
            self.ui.smile_label.setText("👾")
