from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QWidget

from game_state import GameState


class GameWidget(QWidget):
    """
    Qt-based visual wrapper around GameState.
    Draws the ball, timer and clicks; handles mouse clicks.
    """

    def __init__(self, parent=None, rules=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setMouseTracking(True)

        self.player_name = ""
        self.level_name = ""
        self.rules = rules   # <-- add this line

        # Sound effect for ball hits
        self._hit_sound = QSoundEffect(self)
        self._hit_sound.setSource(QUrl.fromLocalFile("assets/hit.wav"))
        self._hit_sound.setVolume(0.25)

        # Sound effect for missed clicks
        self._miss_sound = QSoundEffect(self)
        self._miss_sound.setSource(QUrl.fromLocalFile("assets/miss.wav"))
        self._miss_sound.setVolume(0.30)

        # Game state will be initialised lazily on first resize
        self.state = None

        # 60 FPS timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(16)  # ~60 fps

    def set_player_and_level(self, player: str, level: str):
        self.player_name = player or ""
        self.level_name = level or ""
        self.update()

    def _ensure_state(self):
        if self.state is None:
            w = max(1, self.width())
            h = max(1, self.height())
            self.state = GameState(w, h, duration=10.0, rules=self.rules)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Recreate state whenever size changes significantly
        if self.state is not None:
            self.state.reset(self.width(), self.height())

    def _on_tick(self):
        if self.width() <= 0 or self.height() <= 0:
            return
        self._ensure_state()
        # Update with a fixed dt (approx 1/60s)
        self.state.update(1.0 / 60.0)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._ensure_state()
            hit = self.state.handle_click(event.position().x(), event.position().y())
            if hit:
                if self._hit_sound is not None:
                    self._hit_sound.stop()
                    self._hit_sound.play()
            else:
                if self._miss_sound is not None:
                    self._miss_sound.stop()
                    self._miss_sound.play()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Background
        painter.fillRect(self.rect(), QColor("#FFFFFF"))

        if self.state is None:
            painter.end()
            return

        b = self.state.ball

        # Draw ball
        painter.setBrush(QColor("#FF6666"))
        painter.setPen(Qt.black)
        painter.drawEllipse(
            int(b.x - b.radius),
            int(b.y - b.radius),
            int(2 * b.radius),
            int(2 * b.radius),
        )

        # HUD text
        painter.setPen(Qt.black)
        font = QFont()
        font.setPointSize(12)
        painter.setFont(font)

        text_lines = [
            f"Player: {self.player_name}" if self.player_name else "Player: (none)",
            f"Level: {self.level_name}" if self.level_name else "Level: (none)",
            f"Time left: {self.state.remaining:0.1f}s",
            f"Hits: {self.state.clicks}",
        ]

        x = 10
        y = 20
        for line in text_lines:
            painter.drawText(x, y, line)
            y += 18

        painter.end()
