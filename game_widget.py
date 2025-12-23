import random
# (legacy settings support removed)

from PySide6.QtCore import QTimer, Qt, QUrl, QRect, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QPixmap
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QWidget

from game_state import GameState

# --- Grenade animation phase constants ----------------------------------------

GRENADE_LOB_END = 15
GRENADE_FUSE_START = 16
GRENADE_FUSE_END = 18
GRENADE_EXPLODE_START = 19
GRENADE_LAST_FRAME = 23

GRENADE_LOB_DURATION = 0.8          # seconds for frames 0..15
GRENADE_FUSE_MIN = 2.0              # minimum fuse (defuse window) duration in seconds
GRENADE_FUSE_MAX = 3.0              # maximum fuse (defuse window) duration in seconds
GRENADE_EXPLOSION_DURATION = 0.7    # seconds for frames 19..23


class GameWidget(QWidget):
    """
    Qt-based visual wrapper around GameState.
    Draws the ball, timer and clicks; handles mouse clicks.
    """

    # Emitted once at the end of each round: (player_name, level_name, score)
    roundFinished = Signal(str, str, int)

    def __init__(self, parent=None, rules=None, duration: float | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setMouseTracking(True)

        self.player_name = ""
        self.level_name = ""
        self.rules = rules   # <-- add this line
        self.ball_color = QColor("#FF6666")

        # Grenade animation (Ball_04 only), using individual PNG frames
        self._grenade_frames = []
        for i in range(24):
            path = f"assets/sprites/grenade_{i:02d}.png"
            pix = QPixmap(path)
            if pix.isNull():
                print(f"[DEBUG] Grenade frame missing or invalid: {path}")
            self._grenade_frames.append(pix)

        self._grenade_total_frames = len(self._grenade_frames)
        # Aim for ~5 seconds total animation duration
        self._grenade_frame_duration = 5.0 / max(1, self._grenade_total_frames)

        self._grenade_active = False
        self._grenade_frame = 0
        self._grenade_frame_accum = 0.0
        self._grenade_plays_this_round = 0
        self._grenade_trigger_times = []

        # Grenade phase tracking
        self._grenade_phase = "idle"           # "idle", "lob", "fuse", "explode", "done"
        self._grenade_phase_start_time = 0.0   # round elapsed time when current phase started
        self._grenade_fuse_duration = 0.0      # how long the player has to defuse

        # Cached rect for grenade click hit-testing
        self._grenade_dest_rect = None

        # Track elapsed time in the current round (play phase only)
        # Duration precedence:
        #   1) explicit duration passed by caller (run.py from data/levels.yaml)
        #   2) rules.duration if provided by rules object
        #   3) settings.yaml fallback (legacy)
        if duration is not None:
            self._round_duration = float(duration)
        elif self.rules is not None and hasattr(self.rules, "duration"):
            try:
                self._round_duration = float(getattr(self.rules, "duration"))
            except Exception:
                self._round_duration = self._load_round_duration_from_settings()
        else:
            self._round_duration = self._load_round_duration_from_settings()

        self._round_elapsed = 0.0
        print(f"[DEBUG] Round duration set to {self._round_duration:0.2f}s")

        # Sound effect for ball hits
        self._hit_sound = QSoundEffect(self)
        self._hit_sound.setSource(QUrl.fromLocalFile("assets/hit.wav"))
        self._hit_sound.setVolume(0.25)

        # Sound effect for missed clicks
        self._miss_sound = QSoundEffect(self)
        self._miss_sound.setSource(QUrl.fromLocalFile("assets/miss.wav"))
        self._miss_sound.setVolume(0.80)

        # Game state will be initialised lazily on first resize
        self.state = None

        # 120 FPS timer (use highest precision available)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(8)   # ~120 fps

        # High-resolution timer for smooth delta timing
        from PySide6.QtCore import QElapsedTimer
        self._elapsed_timer = QElapsedTimer()
        self._elapsed_timer.start()

        # Countdown phase before gameplay starts
        self._phase = "countdown"
        self._ready_texts = ["Ready?", "Steady?", "Go!"]
        self._ready_index = 0
        self._ready_timer = 1.5  # seconds per word

        # Track whether we've already emitted the roundFinished signal for this round
        self._round_over_emitted = False

    def set_player_and_level(self, player: str, level: str):
        self.player_name = player or ""
        self.level_name = level or ""
        self.update()

    def _load_round_duration_from_settings(self) -> float:
        """
        Legacy fallback only.
        Round duration is now expected to come from data/levels.yaml via run.py.
        This method exists solely to guarantee a safe default if nothing is provided.
        """
        return 20.0

    def _ensure_state(self):
        if self.state is None:
            w = max(1, self.width())
            h = max(1, self.height())
            self.state = GameState(w, h, duration=self._round_duration, rules=self.rules)

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
            dt = self._elapsed_timer.restart() / 1000.0  # ms -> seconds
            if dt > 0.05:
                dt = 0.05

            self._ready_timer -= dt
            if self._ready_timer <= 0:
                self._ready_index += 1
                if self._ready_index >= len(self._ready_texts):
                    self._phase = "play"
                    self._elapsed_timer.restart()
                    self._start_new_round()
                else:
                    self._ready_timer = 1.5

            self.update()
            return

        self._ensure_state()

        # Real delta-timing for smooth animation (Qt high-resolution clock)
        dt = self._elapsed_timer.restart() / 1000.0  # ms -> seconds

        # Clamp dt to avoid visible jumps if the event loop stalls
        if dt > 0.05:
            dt = 0.05

        self.state.update(dt)
        self._update_grenade(dt)

        # Detect transition to game over and emit score exactly once per round
        if self.state.remaining <= 0.0 and not self._round_over_emitted:
            self._round_over_emitted = True
            score = int(getattr(self.state, "clicks", 0))
            print(f"[DEBUG] Round finished: player={self.player_name}, level={self.level_name}, score={score}")
            self.roundFinished.emit(self.player_name or "", self.level_name or "", score)

        self.update()

    def _start_new_round(self):
        """
        Reset per-round timers and schedule grenade animations for ball04.
        Called when we transition from countdown to play.
        """
        # New round: allow a fresh roundFinished signal
        self._round_over_emitted = False
        self._round_elapsed = 0.0
        self._grenade_active = False
        self._grenade_frame = 0
        self._grenade_frame_accum = 0.0
        self._grenade_plays_this_round = 0
        self._grenade_trigger_times = []
        # Reset grenade phase state
        self._grenade_phase = "idle"
        self._grenade_phase_start_time = 0.0
        self._grenade_fuse_duration = 0.0

        # Only schedule grenade animation for Ball_04 level
        level_key = (self.level_name or "").lower()
        if ("ball_04" not in level_key) and ("ball04" not in level_key) and ("rampage" not in level_key):
            print(f"[DEBUG] Grenade: skipping scheduling, level_name='{self.level_name}'")
            return
        print(
            f"[DEBUG] Grenade: scheduling for level '{self.level_name}' with round_duration={self._round_duration:0.2f}s")

        # Schedule a single grenade animation at a random time between
        # 10% and 70% of the round, leaving enough time for the ~5s animation.
        if self._round_duration <= 0:
            print("[DEBUG] Grenade: round duration is non-positive; skipping scheduling.")
            return

        min_start = max(0.0, self._round_duration * 0.10)
        max_start = min(self._round_duration * 0.70, self._round_duration - 5.0)

        # If the window collapses, fall back to a simple 'early in the round' start.
        if max_start <= min_start:
            min_start = 1.0
            max_start = max(min_start, self._round_duration - 5.0)

        if max_start <= min_start:
            print(f"[DEBUG] Grenade: cannot find a valid trigger window in round_duration={self._round_duration:0.2f}s")
            return

        t = random.uniform(min_start, max_start)
        self._grenade_trigger_times.append(t)
        self._grenade_trigger_times.sort()
        print(f"[DEBUG] Grenade: scheduled trigger at t={t:0.2f}s (window {min_start:0.2f}s–{max_start:0.2f}s)")

    def _update_grenade(self, dt: float):
        """
        Advance grenade animation in three phases (lob, fuse, explode), triggered at a
        random time during the round. Uses round-elapsed time and phase-specific timing
        rather than a fixed frame duration.
        """
        if self._phase != "play":
            return

        # Track elapsed time only during play
        self._round_elapsed += dt

        # If not Ball_04, do nothing
        level_key = (self.level_name or "").lower()
        if ("ball_04" not in level_key) and ("ball04" not in level_key) and ("rampage" not in level_key):
            return

        # Start a grenade animation when we hit the next trigger time
        if (
            not self._grenade_active
            and self._grenade_plays_this_round < 1
            and self._grenade_trigger_times
        ):
            next_trigger = self._grenade_trigger_times[0]
            if self._round_elapsed >= next_trigger:
                self._grenade_trigger_times.pop(0)
                self._grenade_active = True
                self._grenade_phase = "lob"
                self._grenade_phase_start_time = self._round_elapsed
                self._grenade_fuse_duration = random.uniform(GRENADE_FUSE_MIN, GRENADE_FUSE_MAX)
                self._grenade_frame = 0
                self._grenade_frame_accum = 0.0

                print(
                    f"[DEBUG] Grenade animation START at {self._round_elapsed:0.2f}s "
                    f"(fuse window={self._grenade_fuse_duration:0.2f}s)"
                )

        if not self._grenade_active or self._grenade_total_frames <= 0:
            return

        # Phase-specific frame updates
        now = self._round_elapsed
        phase_time = now - self._grenade_phase_start_time

        # Safety clamp for frame index
        max_frame_index = self._grenade_total_frames - 1

        if self._grenade_phase == "lob":
            # Map time 0..GRENADE_LOB_DURATION -> frames 0..GRENADE_LOB_END
            duration = max(0.01, GRENADE_LOB_DURATION)
            progress = min(1.0, max(0.0, phase_time / duration))
            frame_span = GRENADE_LOB_END + 1  # frames 0..15 inclusive
            frame = int(progress * frame_span)
            self._grenade_frame = max(0, min(frame, GRENADE_LOB_END))

            if progress >= 1.0:
                # Transition into fuse phase
                self._grenade_phase = "fuse"
                self._grenade_phase_start_time = now
                self._grenade_frame = GRENADE_FUSE_START
                print(
                    f"[DEBUG] Grenade phase -> FUSE at {now:0.2f}s "
                    f"(duration={self._grenade_fuse_duration:0.2f}s)"
                )

        elif self._grenade_phase == "fuse":
            # Grenade is settled; loop gently over frames 16..18 while the player can defuse.
            if phase_time < self._grenade_fuse_duration:
                loop_len = GRENADE_FUSE_END - GRENADE_FUSE_START + 1  # typically 3 frames
                if self._grenade_fuse_duration <= 0:
                    ratio = 0.0
                else:
                    ratio = (phase_time / self._grenade_fuse_duration) % 1.0
                offset = int(ratio * loop_len)
                self._grenade_frame = max(
                    GRENADE_FUSE_START,
                    min(GRENADE_FUSE_START + offset, GRENADE_FUSE_END),
                )
            else:
                # Time's up: start explosion phase and end the round.
                self._grenade_phase = "explode"
                self._grenade_phase_start_time = now
                self._grenade_frame = GRENADE_EXPLODE_START
                print(f"[DEBUG] Grenade phase -> EXPLODE at {now:0.2f}s (player failed to defuse)")

                # Mark the round as ended, but keep the timer running so the explosion
                # animation can play while the Game Over text is shown.
                if self.state is not None:
                    self.state.remaining = 0.0

        elif self._grenade_phase == "explode":
            # Play frames GRENADE_EXPLODE_START..GRENADE_LAST_FRAME over GRENADE_EXPLOSION_DURATION
            duration = max(0.01, GRENADE_EXPLOSION_DURATION)
            progress = min(1.0, max(0.0, phase_time / duration))
            span = GRENADE_LAST_FRAME - GRENADE_EXPLODE_START + 1
            offset = int(progress * span)
            frame = GRENADE_EXPLODE_START + offset
            self._grenade_frame = max(GRENADE_EXPLODE_START, min(frame, GRENADE_LAST_FRAME))

            if progress >= 1.0 or self._grenade_frame >= GRENADE_LAST_FRAME:
                # Explosion finished; grenade animation done for this round.
                self._grenade_phase = "done"
                self._grenade_active = False
                self._grenade_frame = GRENADE_LAST_FRAME
                self._grenade_plays_this_round += 1
                print(
                    f"[DEBUG] Grenade animation END (EXPLODED) at {self._round_elapsed:0.2f}s "
                    f"(plays so far: {self._grenade_plays_this_round})"
                )

        else:
            # "idle" or "done" – nothing to animate
            return

        # Clamp final frame index as a safety net
        if self._grenade_frame < 0:
            self._grenade_frame = 0
        elif self._grenade_frame > max_frame_index:
            self._grenade_frame = max_frame_index

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # If a grenade is active, only grenade clicks are allowed.
            if self._grenade_active:
                # Use the same rect as in paintEvent for hit-testing
                if self._grenade_dest_rect is None:
                    self._grenade_dest_rect = self._compute_grenade_dest_rect(self._grenade_frame)

                if self._grenade_dest_rect.contains(int(event.position().x()), int(event.position().y())):
                    if self._grenade_phase in ("lob", "fuse"):
                        # Grenade successfully defused: stop the animation and allow play to continue.
                        self._grenade_active = False
                        self._grenade_phase = "done"
                        self._grenade_plays_this_round += 1
                        print(f"[DEBUG] Grenade DEFUSED at {self._round_elapsed:0.2f}s")
                    else:
                        # Too late to defuse (explosion already in progress)
                        print(
                            f"[DEBUG] Grenade click during phase '{self._grenade_phase}' "
                            f"at {self._round_elapsed:0.2f}s (too late to defuse)"
                        )
                else:
                    # Click outside grenade while it's active: ignore completely
                    print(f"[DEBUG] Click ignored while grenade active at {self._round_elapsed:0.2f}s")
                self.update()
                return

            # Normal ball-click behaviour when no grenade is active
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

    def _grenade_vertical_offset(self, frame_index: int, dest_size: int) -> int:
        """
        Returns a vertical offset (in pixels) above the floor for the grenade.
        Positive values move the grenade upwards (i.e. away from the floor).
        Uses simple piecewise parabolas over the 24-frame animation:
        - Frames 0-5: initial lob in, from high to floor.
        - Frames 6-11: first (larger) bounce.
        - Frames 12-15: second (smaller) bounce.
        - Frames 16+: settled on the floor (no offset).
        """
        # Safety clamp
        if frame_index < 0:
            frame_index = 0
        if frame_index >= self._grenade_total_frames:
            frame_index = self._grenade_total_frames - 1

        # Phase 1: lob in (frames 0-5) - start high, fall towards floor
        if frame_index <= 5:
            t = frame_index / 5.0  # 0..1
            max_offset = int(dest_size * 1.2)  # about 1.2 grenade heights above floor
            # High at t=0, near floor at t=1
            return int(max_offset * (1.0 - t))

        # Phase 2: first bounce (frames 6-11) - symmetric small arc
        if frame_index <= 11:
            t = (frame_index - 6) / 5.0  # 0..1 over 6 frames
            max_offset = int(dest_size * 0.6)
            # Simple parabola with peak at t=0.5
            return int(max_offset * 4.0 * t * (1.0 - t))

        # Phase 3: second bounce (frames 12-15) - even smaller arc
        if frame_index <= 15:
            t = (frame_index - 12) / 3.0  # 0..1 over 4 frames
            max_offset = int(dest_size * 0.3)
            return int(max_offset * 4.0 * t * (1.0 - t))

        # Phase 4: settled on the floor for the rest of the frames
        return 0

    def _compute_grenade_dest_rect(self, frame_index: int) -> QRect:
        """
        Compute the destination rect for drawing the grenade sprite.

        The grenade is drawn as a 64x64 px image in the bottom-right corner
        of the play area, sitting on an internal "room floor" that is
        noticeably above the widget bottom. The frame_index is currently
        unused but kept for API compatibility.
        """
        dest_size = 64  # fixed display size in pixels

        # Pull the grenade a bit away from the right "wall" so the
        # left edge of the animation has some breathing room.
        right_margin = 20
        grenade_x_offset = 80  # pixels left from the usual right-edge placement
        dest_x = max(0, self.width() - dest_size - right_margin - grenade_x_offset)

        # Define a room floor some pixels above the widget bottom so that
        # the grenade/explosion appears clearly inside the game area.
        # You can tweak room_floor_offset after visual inspection.
        room_floor_offset = 0  # pixels up from the bottom of the widget
        floor_y = self.height() - room_floor_offset

        # Ensure we don't go off the top if the widget is very small
        dest_y = max(0, floor_y - dest_size)

        return QRect(dest_x, dest_y, dest_size, dest_size)

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

        # If the round has ended, show a Game Over message instead of the ball
        if self.state.remaining <= 0.0:
            painter.setPen(Qt.black)
            font = QFont()
            font.setPointSize(36)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "Game Over")
        else:
            # Draw ball (normal play mode)
            painter.setBrush(self.ball_color)
            painter.setPen(Qt.black)
            painter.drawEllipse(
                int(b.x - b.radius),
                int(b.y - b.radius),
                int(2 * b.radius),
                int(2 * b.radius),
            )

        # Draw grenade animation inside the game area (Ball_04 only)
        level_key = (self.level_name or "").lower()
        if (
                ("ball_04" in level_key or "ball04" in level_key or "rampage" in level_key)
                and self._grenade_active
                and self._grenade_total_frames > 0
        ):
            frame_index = max(0, min(self._grenade_frame, self._grenade_total_frames - 1))
            pix = self._grenade_frames[frame_index]
            if not pix.isNull():
                dest_rect = self._compute_grenade_dest_rect(frame_index)
                base_floor_y = dest_rect.bottom()
                print(f"[DEBUG] Grenade base rect frame={frame_index}, bottom={base_floor_y}, widget_height={self.height()}")

                # Apply stronger scaling from frame 17 onward so that growth is clearly visible
                scaled_pix = pix
                if frame_index >= 17:
                    # Linearly ramp from 1.0x at frame 17 up to ~2.0x at the final frame
                    start_idx = 17
                    steps = max(1, self._grenade_total_frames - start_idx - 1)
                    progress = max(0, min(frame_index - start_idx, steps))
                    scale_factor = 1.0 + 10.0 * (progress / steps)

                    # Compute new size
                    new_w = int(dest_rect.width() * scale_factor)
                    new_h = int(dest_rect.height() * scale_factor)
                    scaled_pix = pix.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                    # Keep the grenade's feet anchored to the same floor line as the base 64x64 sprite.
                    # Use the bottom of the original (unscaled) dest_rect as the floor Y.
                    cx = dest_rect.center().x()
                    floor_y = dest_rect.bottom()
                    dest_rect = QRect(cx - new_w // 2, floor_y - new_h + 1, new_w, new_h)

                    # Extended debug: show scaled bottom and floor reference
                    scaled_bottom = dest_rect.bottom()
                    print(
                        f"[DEBUG] Grenade scale frame={frame_index}, "
                        f"factor={scale_factor:.2f}, size={new_w}x{new_h}, "
                        f"floor_y={floor_y}, scaled_bottom={scaled_bottom}, widget_height={self.height()}"
                    )

                self._grenade_dest_rect = dest_rect
                painter.drawPixmap(dest_rect, scaled_pix)

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
