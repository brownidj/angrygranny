import json
import os
import subprocess
import sys
import threading
import time
from tkinter import messagebox

from utilities import load_level_names  # Import the utility function


class GameLauncher:
    """
    Launches the Angry Granny py5 game as a subprocess, handles score retrieval,
    updates high scores via PlayerManager, and prompts for replay.
    """

    def __init__(self, root, player_manager, sound_on: bool):
        self.root = root
        self.pm = player_manager
        self.sound_on = sound_on
        # Load level mappings once
        self.level_mappings = load_level_names()

    def run(self, player: str, level: str):
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

                        # Use consolidated level mappings
                        level_mapping = self.level_mappings.get(level, level)

                        # Update the message to use the player level mapping
                        msg = player + " scored " + str(score) + " on\n" + str(level_mapping) + ".\n"

                        if score > high:
                            self.pm.set_high_score(player, level, score)
                            msg += "\n" + "🎉 New high score!"
                        else:
                            msg += "\nCurrent high score: " + str(high) + "."
                        os.remove(result_file)
                    else:
                        msg = "Game finished, but you didn't improve your score"

                    # Prompt for replay (ask on Tk main thread)
                    msg += "\n\nPlay again?"
                    again = self._ask_yes_no_on_main("Game Over", msg)
                    if not again:
                        # Close all windows and end the game
                        self._shutdown_app()
                        break

                    # Small delay before restarting
                    time.sleep(1)

            except Exception as e:
                print("Exception in game launcher thread:", e)
                self.root.after(0, lambda err=e: messagebox.showerror("Error", str(err)))

        threading.Thread(target=_game_thread, daemon=True).start()

    # -------------------------------
    # Utilities (thread-safe UI)
    # -------------------------------
    def _ask_yes_no_on_main(self, title: str, message: str) -> bool:
        """Synchronously ask a yes/no dialog on the Tk main thread and return the result."""
        result = {"ans": False}
        done = threading.Event()

        def _show():
            try:
                result["ans"] = messagebox.askyesno(title, message)
            finally:
                done.set()

        self.root.after(0, _show)
        done.wait()
        return bool(result["ans"])

    def _shutdown_app(self):
        """Destroy all Tk windows and exit the app from the Tk main thread."""
        def _do_shutdown():
            try:
                # Destroy all toplevel windows first
                try:
                    for w in list(self.root.winfo_children()):
                        try:
                            w.destroy()
                        except Exception:
                            pass
                except Exception:
                    pass
                # Quit and destroy root
                try:
                    self.root.quit()
                except Exception:
                    pass
                try:
                    self.root.destroy()
                except Exception:
                    pass
            except Exception as e:
                print("Error during shutdown:", e)
        # Ensure shutdown occurs on the Tk main loop
        self.root.after(0, _do_shutdown)
