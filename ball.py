import random
from abc import ABC, abstractmethod

class Ball(ABC):
    """
    Abstract base class for a bouncing ball with a separate direction and velocity.
    """
    def __init__(self, x, y, radius, ball_fill):
        self.x = x
        self.y = y
        self.radius = radius
        self.ball_fill = ball_fill
        # Direction multipliers: 1 or -1
        self.x_dir = 1
        self.y_dir = 1
        # Velocity magnitudes (step sizes)
        self.x_vel = 0
        self.y_vel = 0
        # Initialise velocity magnitudes
        self.set_velocity()

    def display(self, sketch):
        sketch.fill(self.ball_fill)
        sketch.ellipse(self.x, self.y, self.radius * 2, self.radius * 2)

    def move(self, sketch):
        """
        Move the ball by its velocity and direction, then handle collisions.
        """
        self.x += self.x_vel * self.x_dir
        self.y += self.y_vel * self.y_dir
        self.check_collision(sketch)

    def check_collision(self, sketch):
        """
        Reverse direction multipliers on canvas edge collisions.
        """
        if not (self.radius <= self.x <= sketch.width - self.radius):
            self.x_dir *= -1
        if not (self.radius <= self.y <= sketch.height - self.radius):
            self.y_dir *= -1

    def ball_clicked(self, mouse_x, mouse_y, sketch):
        """
        Check click within ball and change color if clicked.
        Returns True if clicked.
        """
        if sketch.dist(mouse_x, mouse_y, self.x, self.y) <= self.radius:
            self.ball_fill = sketch.color(
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )
            return True
        return False

    def on_click(self):
        """
        Handle click event: by default, reset velocity magnitudes.
        Subclasses may override to change direction only.
        """
        self.set_velocity()

    @abstractmethod
    def set_velocity(self):
        """
        Abstract: set self.x_vel and self.y_vel to define speed.
        """
        pass

class Ball01(Ball):
    """
    Relaxed speed: constant velocity and direction.
    Direction only changes on collision; clicks have no effect.
    """
    def set_velocity(self):
        # Set constant velocity magnitudes
        self.x_vel = 2.5
        self.y_vel = 1.4

class Ball02(Ball):
    """
    Easy speed: random velocity on instantiation and on click.
    Velocity resets to new random magnitudes when clicked.
    """
    def on_click(self):
        """
        On click, reset velocity and 30% chance to reverse travel direction.
        """
        # Reset velocity magnitudes
        super().on_click()
        # 30% chance to reverse direction
        if random.random() < 0.3:
            self.x_dir *= -1
            self.y_dir *= -1

    def set_velocity(self):
        # Set velocity magnitudes once
        self.x_vel = random.uniform(2, 4)
        self.y_vel = random.uniform(1, 3)

class Ball03(Ball):
    """
    Medium speed: random velocity on instantiation and on click.
    Velocity resets to new random magnitudes on click; 60% chance on click to
    change direction: reverse or perpendicular.
    """
    def on_click(self):
        # Reset velocity magnitudes
        super().on_click()
        # 60% chance to change direction
        if random.random() < 0.6:
            # 50/50 between reverse and perpendicular change
            if random.random() < 0.5:
                # reverse direction
                self.x_dir *= -1
                self.y_dir *= -1
            else:
                # perpendicular change: clockwise or counterclockwise
                if random.random() < 0.5:
                    # clockwise 90°
                    new_x_dir = self.y_dir
                    new_y_dir = -self.x_dir
                else:
                    # counterclockwise 90°
                    new_x_dir = -self.y_dir
                    new_y_dir = self.x_dir
                self.x_dir, self.y_dir = new_x_dir, new_y_dir

    def set_velocity(self):
        # Random velocity magnitudes for Medium
        self.x_vel = random.uniform(3, 5)
        self.y_vel = random.uniform(2, 4)

class Ball04(Ball):

    def set_velocity(self):
        pass