import random
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
        self.ball_color = QColor("#FF6666")

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

        # 120 FPS timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(8)   # ~120 fps

        # Track last frame time for real delta timing
        self._last_time = None

        # Countdown phase before gameplay starts
        self._phase = "countdown"
        self._ready_texts = ["Ready?", "Steady?", "Go!"]
        self._ready_index = 0
        self._ready_timer = 1.5  # seconds per word

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

        # Countdown handling: Ready / Steady / Go
        if self._phase == "countdown":
            import time
            current = time.perf_counter()
            if self._last_time is None:
                dt = 1.0 / 120.0
            else:
                dt = current - self._last_time
            self._last_time = current

            if dt > 0.05:
                dt = 0.05

            self._ready_timer -= dt
            if self._ready_timer <= 0:
                self._ready_index += 1
                if self._ready_index >= len(self._ready_texts):
                    self._phase = "play"
                    self._last_time = None
                else:
                    self._ready_timer = 1.5

            self.update()
            return

        self._ensure_state()

        # Real delta-timing for smooth animation
        now = QTimer.remainingTime(self._timer)  # dummy call to access QtCore
        import time
        current = time.perf_counter()
        if self._last_time is None:
            dt = 1.0 / 120.0
        else:
            dt = current - self._last_time
        self._last_time = current

        # Clamp dt to avoid huge jumps on window stall
        if dt > 0.05:
            dt = 0.05

        self.state.update(dt)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._ensure_state()
            hit = self.state.handle_click(event.position().x(), event.position().y())
            if hit:
                if self._hit_sound is not None:
                    self._hit_sound.stop()
                    self._hit_sound.play()
                # On a successful hit, change the ball to a random colour
                self.ball_color = QColor(
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255),
                )
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

        # Countdown phase: Ready / Steady / Go
        if self._phase == "countdown":
            painter.setPen(Qt.black)
            font = QFont()
            font.setPointSize(48)
            painter.setFont(font)

            text = self._ready_texts[self._ready_index]
            painter.drawText(self.rect(), Qt.AlignCenter, text)

            painter.end()
            return

        # Ensure game state exists for normal play mode
        self._ensure_state()
        if self.state is None:
            painter.end()
            return

        b = self.state.ball

        # Draw ball (normal play mode)
        painter.setBrush(self.ball_color)
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
