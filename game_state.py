import math
import random
from dataclasses import dataclass
from typing import Protocol

class LevelRules(Protocol):
    def initial_velocity(self, ball: "Ball"):
        ...

    def on_click(self, ball: "Ball"):
        ...

class Ball01Rules:
    """
    Relaxed speed: constant velocity and direction.
    Direction only changes on collision; clicks have no effect.
    """
    def initial_velocity(self, ball):
        # Original Ball01 speeds were 2.5 and 1.4 pixels per frame at ~60 FPS.
        # Convert to pixels per second: speed * 60.
        speed_x = 2.5 * 60.0
        speed_y = 1.4 * 60.0
        # Randomise initial direction
        ball.vx = speed_x if random.random() < 0.5 else -speed_x
        ball.vy = speed_y if random.random() < 0.5 else -speed_y

    def on_click(self, ball):
        # Ball01 clicks have no effect on velocity/direction.
        # All behaviour changes come from wall collisions handled in GameState.
        return

class Ball02Rules:
    """
    Easy speed: random velocity on instantiation and on click.
    Velocity resets to new random magnitudes when clicked, with a 30% chance
    to reverse travel direction.
    """
    def _set_random_velocity(self, ball):
        # Original Ball02 used:
        #   x_vel in [2, 4], y_vel in [1, 3] pixels per frame.
        # Convert to per-second speeds for our dt-based update.
        speed_x = random.uniform(2.0, 4.0) * 60.0
        speed_y = random.uniform(1.0, 3.0) * 60.0
        # Random initial direction
        ball.vx = speed_x if random.random() < 0.5 else -speed_x
        ball.vy = speed_y if random.random() < 0.5 else -speed_y

    def initial_velocity(self, ball):
        self._set_random_velocity(ball)

    def on_click(self, ball):
        # Reset velocity magnitudes (new random speeds and possibly direction).
        self._set_random_velocity(ball)
        # 30% chance to reverse travel direction
        if random.random() < 0.3:
            ball.vx *= -1.0
            ball.vy *= -1.0

class Ball03Rules:
    """
    Medium speed: random velocity on instantiation and on click.
    Velocity resets to new random magnitudes on click; 60% chance on click to
    change direction: reverse or perpendicular.
    """
    def _set_random_velocity(self, ball):
        # Original Ball03 used:
        #   x_vel in [3, 5], y_vel in [2, 4] pixels per frame.
        speed_x = random.uniform(3.0, 5.0) * 60.0
        speed_y = random.uniform(2.0, 4.0) * 60.0
        ball.vx = speed_x if random.random() < 0.5 else -speed_x
        ball.vy = speed_y if random.random() < 0.5 else -speed_y

    def initial_velocity(self, ball):
        self._set_random_velocity(ball)

    def on_click(self, ball):
        # Reset velocity magnitudes
        self._set_random_velocity(ball)
        # 60% chance to change direction
        if random.random() < 0.6:
            if random.random() < 0.5:
                # Reverse direction
                ball.vx *= -1.0
                ball.vy *= -1.0
            else:
                # Perpendicular change: clockwise or counterclockwise
                if random.random() < 0.5:
                    # clockwise 90°: (vx, vy) -> (vy, -vx)
                    new_vx = ball.vy
                    new_vy = -ball.vx
                else:
                    # counterclockwise 90°: (vx, vy) -> (-vy, vx)
                    new_vx = -ball.vy
                    new_vy = ball.vx
                ball.vx, ball.vy = new_vx, new_vy

class Ball04Rules:
    """
    Hard speed: faster random velocity and more chaotic behaviour.
    Velocity resets on click, always changing direction (reverse or perpendicular),
    and the ball shrinks slightly on each successful click.
    """
    def _set_random_velocity(self, ball):
        # A bit faster than Ball03: x_vel in [4, 7], y_vel in [3, 5] pixels/frame.
        speed_x = random.uniform(4.0, 7.0) * 60.0
        speed_y = random.uniform(3.0, 5.0) * 60.0
        ball.vx = speed_x if random.random() < 0.5 else -speed_x
        ball.vy = speed_y if random.random() < 0.5 else -speed_y

    def initial_velocity(self, ball):
        self._set_random_velocity(ball)

    def on_click(self, ball):
        # Reset velocity magnitudes
        self._set_random_velocity(ball)
        # Always change direction in some way
        if random.random() < 0.5:
            # Reverse
            ball.vx *= -1.0
            ball.vy *= -1.0
        else:
            # Perpendicular change
            if random.random() < 0.5:
                new_vx = ball.vy
                new_vy = -ball.vx
            else:
                new_vx = -ball.vy
                new_vy = ball.vx
            ball.vx, ball.vy = new_vx, new_vy

        # Shrink radius slightly to increase difficulty over hits
        ball.radius *= 0.97

@dataclass
class Ball:
    x: float
    y: float
    radius: float
    vx: float
    vy: float

class GameState:
    """
    Framework-agnostic game logic:
    - one moving ball
    - click detection
    - timer
    - score
    """

    def __init__(self, width: int, height: int, duration: float = 10.0, rules: LevelRules = None):
        self.width = width
        self.height = height
        self.duration = duration
        self.remaining = duration
        self.clicks = 0
        self.over = False
        self.rules = rules or Ball01Rules()

        # Simple ball initialisation
        r = min(width, height) * 0.12
        self.ball = Ball(
            x=width * 0.5,
            y=height * 0.5,
            radius=r,
            vx=width * 0.25,
            vy=height * 0.2,
        )
        self.rules.initial_velocity(self.ball)

    def update(self, dt: float):
        if self.over:
            return

        self.remaining -= dt
        if self.remaining <= 0:
            self.remaining = 0
            self.over = True

        b = self.ball
        b.x += b.vx * dt
        b.y += b.vy * dt

        # Bounce off edges
        if b.x - b.radius < 0 or b.x + b.radius > self.width:
            b.vx *= -1
            b.x = max(b.radius, min(self.width - b.radius, b.x))

        if b.y - b.radius < 0 or b.y + b.radius > self.height:
            b.vy *= -1
            b.y = max(b.radius, min(self.height - b.radius, b.y))

    def handle_click(self, x: float, y: float):
        if self.over:
            return False
        b = self.ball
        dx = x - b.x
        dy = y - b.y
        if math.hypot(dx, dy) <= b.radius:
            self.clicks += 1
            self.rules.on_click(b)
            return True
        return False

    def reset(self, width: int, height: int):
        self.__init__(width, height, self.duration, self.rules)