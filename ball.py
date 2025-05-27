import random

class Ball:
    def __init__(self, x, y, radius, ball_fill):
        self.radius = radius
        self.x = x
        self.y = y
        self.x_move = random.uniform(2, 4) * (-1 if random.random() < 0.5 else 1)
        self.y_move = random.uniform(1, 2.5) * (-1 if random.random() < 0.5 else 1)
        self.ball_fill = ball_fill

    def display(self, p):
        p.fill(self.ball_fill)
        p.ellipse(self.x, self.y, self.radius * 2, self.radius * 2)

    def check_collision(self, p):
        if not (self.radius <= self.x <= p.width - self.radius):
            self.x_move *= -1
        if not (self.radius <= self.y <= p.height - self.radius):
            self.y_move *= -1

    def move(self, p):
        self.check_collision(p)
        self.x += self.x_move
        self.y += self.y_move

    def ball_clicked(self, mouse_x, mouse_y, p):
        if p.dist(mouse_x, mouse_y, self.x, self.y) <= self.radius:
            self.ball_fill = p.color(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            return True
        return False

    def change_speed(self):
        self.x_move = random.uniform(2, 4) * (-1 if random.random() < 0.3 else 1)
        self.y_move = random.uniform(1, 2.5) * (-1 if random.random() < 0.3 else 1)