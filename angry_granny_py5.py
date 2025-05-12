import sys
import py5
import pygame
import json
import os

from ball import Ball
from game_timer import GameTimer

# Initialize pygame mixer
pygame.mixer.init()
pop_sound = pygame.mixer.Sound("ball.mp3")

game_ended = False

# Parse command-line args
if len(sys.argv) >= 3:
    player_name = sys.argv[1]
    player_level = sys.argv[2]
else:
    player_name = "Unknown"
    player_level = "Unknown"

ball = Ball(100, 200, 60, py5.color(255, 0, 0))
click_count = 0
game_timer = GameTimer(20)

def setup():
    py5.size(500, 400)
    py5.frame_rate(60)
    game_timer.start()
    py5.no_stroke()

def draw():
    global game_ended
    py5.background(255)
    remaining_time = game_timer.remaining_time()

    if game_timer.is_running():
        ball.move(py5)
        ball.display(py5)
        display_player_info()
        display_click_count()
        display_timer(remaining_time)
    elif not game_ended:
        display_game_over()
        game_ended = True

def mouse_pressed():
    global click_count
    if ball.ball_clicked(py5.mouse_x, py5.mouse_y, py5):
        click_count += 1
        ball.change_speed()
        pop_sound.play()

def display_player_info():
    py5.fill(50)
    py5.text_size(14)
    py5.text(f"Player: {player_name}", 20, 20)
    py5.text(f"Level: {player_level}", 20, 40)

def display_click_count():
    py5.fill(0)
    py5.text_size(20)
    py5.text("Clicks: " + str(click_count), 20, 70)

def display_timer(remaining_time):
    py5.fill(0)
    py5.text_size(20)
    py5.text("Time: " + str(remaining_time), py5.width - 80, 70)

def display_game_over():
    py5.background(255)
    py5.fill(0)
    py5.text_size(30)
    py5.text_align(py5.CENTER, py5.CENTER)
    py5.text("Game Over!", py5.width / 2, py5.height / 2 - 20)
    py5.text("Final Clicks: " + str(click_count), py5.width / 2, py5.height / 2 + 20)

    # Optional: write score if it beats previous
    if os.path.exists("players.json"):
        with open("players.json", "r") as f:
            players = json.load(f)

        if player_name in players:
            current_high = players[player_name]["high_scores"].get(player_level, 0)
            if click_count > current_high:
                with open("last_score.json", "w") as f_out:
                    json.dump({
                        "player": player_name,
                        "level": player_level,
                        "score": click_count
                    }, f_out)
                print(f"New high score for {player_name} on {player_level}: {click_count}")
            else:
                print(f"Score {click_count} did not beat high score {current_high}")

py5.run_sketch()