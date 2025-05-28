import os
import sys
import subprocess
import threading
import time
import json
from tkinter import messagebox

class GameLauncher:
    """
    Launches the Angry Granny py5 game as a subprocess, handles score retrieval,
    updates high scores via PlayerManager, and prompts for replay.
    """
    def __init__(self, root, player_manager, sound_on: bool):
        self.root = root
        self.pm = player_manager
        self.sound_on = sound_on

    def run(self, player: str, level: str):
        """
        Starts the game loop in a background thread.
        """
        def _game_thread():
            try:
                while True:
                    # Build command
                    args = [sys.executable, "angry_granny_py5.py", player, level]
                    if not self.sound_on:
                        args.append("--mute")

                    # Launch subprocess
                    proc = subprocess.Popen(args)
                    proc.wait()

                    # Retrieve score
                    result_file = "last_score.json"
                    if os.path.exists(result_file):
                        with open(result_file, "r") as f:
                            res = json.load(f)
                        score = res.get("score", 0)
                        high = self.pm.get_high_score(player, level)
                        msg = f"{player} scored {score} on {level}.\n"
                        if score > high:
                            self.pm.set_high_score(player, level, score)
                            msg += "🎉 New high score!"
                        else:
                            msg += f"Current high score: {high}."
                        os.remove(result_file)
                    else:
                        msg = "Game finished but no score recorded."

                    # Prompt for replay
                    msg += "\n\nPlay again?"
                    again = messagebox.askyesno("Game Over", msg)
                    if not again:
                        break

                    # Small delay before restarting
                    time.sleep(1)

            except Exception as e:
                print("Exception in game launcher thread:", e)
                # Capture exception in lambda default arg
                self.root.after(0, lambda err=e: messagebox.showerror("Error", str(err)))

        threading.Thread(target=_game_thread, daemon=True).start()