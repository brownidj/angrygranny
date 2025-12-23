import os
import sys
from PySide6.QtCore import QTimer, Qt, QRect
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import QApplication, QWidget, QLineEdit


class GrenadeAnimationPlayer(QWidget):
    def __init__(self, sprites_dir=None, frame_duration=0.2):
        super().__init__()

        self.filename_display = QLineEdit(self)
        self.filename_display.setReadOnly(True)
        self.filename_display.setGeometry(10, 10, 180, 28)

        # Resolve sprites_dir relative to this file by default, so it works
        # regardless of the current working directory used to launch the script.
        if sprites_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.sprites_dir = os.path.abspath(os.path.join(base_dir, "..", "assets", "sprites"))
        else:
            self.sprites_dir = sprites_dir

        print(f"[DEBUG] Using sprites_dir={self.sprites_dir}")
        self.frame_duration = frame_duration

        # Load frames
        self.frames = []
        for i in range(24):
            path = os.path.join(self.sprites_dir, f"grenade_{i:02d}.png")
            pix = QPixmap(path)
            if pix.isNull():
                print(f"[WARN] Missing frame: {path}")
            self.frames.append(pix)

        self.total_frames = len(self.frames)
        self.current_frame = 0

        # Setup window
        self.setWindowTitle("Grenade Animation Preview")
        self.resize(200, 200)

        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.timer.start(int(self.frame_duration * 1000))

    def next_frame(self):
        self.current_frame = (self.current_frame + 1) % self.total_frames
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        pix = self.frames[self.current_frame]
        if not pix.isNull():
            current_path = os.path.join(self.sprites_dir, f"grenade_{self.current_frame:02d}.png")
            self.filename_display.setText(os.path.basename(current_path))
            # Scale to 64x64 like the game
            scaled = pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2 + 20
            painter.drawPixmap(QRect(x, y, scaled.width(), scaled.height()), scaled)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    duration = 2  # seconds per frame
    player = GrenadeAnimationPlayer(frame_duration=duration)
    player.show()

    sys.exit(app.exec())