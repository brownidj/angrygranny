import json
import os
import subprocess
import sys
import threading
import time
import re
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
        # Create a normalized-key view of level names so lookups work with 'ball01', 'ball_01', etc.
        self.level_mappings_norm = {}
        try:
            for k, v in dict(self.level_mappings).items():
                nk = self._normalize_level_name(k)
                self.level_mappings_norm[nk] = v
        except Exception:
            self.level_mappings_norm = {}
        self.level_thresholds = self._load_level_thresholds()
        # Resolve the py5 script path once
        self._game_script = self._resolve_game_script_path("angry_granny_py5.py")

    def run(self, player: str, level: str):
        def _game_thread():
            current_level = self._normalize_level_name(level)
            try:
                while True:
                    # Build command
                    args = [sys.executable, self._game_script, player, current_level]
                    if not self.sound_on:
                        args.append("--mute")

                    # Launch subprocess
                    proc = subprocess.Popen(args)
                    proc.wait()

                    # Default score in case no result file is written
                    score = 0

                    # Retrieve score
                    result_file = "last_score.json"
                    if os.path.exists(result_file):
                        with open(result_file, "r") as f:
                            res = json.load(f)
                        score = res.get("score", 0)
                        high = self.pm.get_high_score(player, current_level)

                        # Use consolidated level mappings
                        level_mapping = self.level_mappings_norm.get(current_level, current_level)

                        # Update the message to use the player level mapping
                        msg = player + " scored " + str(score) + " on\n" + str(level_mapping) + ".\n"

                        if score > high:
                            self.pm.set_high_score(player, current_level, score)
                            msg += "\n" + "🎉 New high score!"
                        else:
                            msg += "\nCurrent high score: " + str(high) + "."
                        os.remove(result_file)
                    else:
                        msg = "Game finished, but you didn't improve your score"

                    # Determine if player can level up based on constants.txt
                    can_level_up = False
                    next_level = self._get_next_level(current_level)
                    threshold = self.level_thresholds.get(self._normalize_level_name(current_level))
                    if threshold is not None and score >= threshold and next_level is not None:
                        can_level_up = True

                    if can_level_up:
                        # 3-option dialog: Exit / Continue / Level up
                        msg += "\n\nYou reached the score required to level up."
                        msg += "\nRequired: " + str(threshold) + ", You scored: " + str(score) + "."
                        msg += "\n\nChoose: Exit, Continue, or Level up."
                        choice = self._ask_replay_choice_on_main("Game Over", msg, show_level_up=True)
                        if choice == "exit":
                            self._shutdown_app()
                            break
                        elif choice == "level_up":
                            current_level = next_level
                            # brief pause before starting next level
                            time.sleep(1)
                            continue
                        else:
                            # continue same level
                            time.sleep(1)
                            continue
                    else:
                        # 2-option dialog: Continue Level / Exit
                        msg += "\n\nDo you want to continue?"
                        again = self._ask_yes_no_on_main("Game Over", msg)
                        if not again:
                            self._shutdown_app()
                            break
                        time.sleep(1)
                        continue

            except Exception as e:
                print("Exception in game launcher thread:", e)
                self.root.after(0, lambda err=e: messagebox.showerror("Error", str(err)))

        threading.Thread(target=_game_thread, daemon=True).start()

    # -------------------------------
    # Utilities (thread-safe UI)
    # -------------------------------
    def _ask_yes_no_on_main(self, title: str, message: str) -> bool:
        """Synchronously ask a yes/no dialog on the Tk main thread and return the result.
        The dialog buttons simulate 'Continue Level' (Yes) and 'Exit' (No) options.
        """
        result = {"ans": False}
        done = threading.Event()

        def _show():
            try:
                # Although tkinter does not allow changing button labels directly,
                # we interpret 'Yes' as 'Continue Level' and 'No' as 'Exit'.
                choice = messagebox.askquestion(title, message, icon='question', type='yesno', default='yes')
                # Interpret 'yes' as 'Continue Level', 'no' as 'Exit'
                result["ans"] = (choice == 'yes')
            finally:
                done.set()

        self.root.after(0, _show)
        done.wait()
        return bool(result["ans"])

    def _ask_replay_choice_on_main(self, title, message, show_level_up=False):
        """Show a modal dialog on the Tk main thread with buttons:
        - If show_level_up: [Exit] [Continue] [Level up]
        - Else: fall back to 2-button behavior via _ask_yes_no_on_main
        Returns one of: 'exit', 'continue', 'level_up'.
        """
        if not show_level_up:
            return "continue" if self._ask_yes_no_on_main(title, message) else "exit"

        result = {"choice": "continue"}
        done = threading.Event()

        def _show_dialog():
            import tkinter as tk
            win = tk.Toplevel(self.root)
            win.title(title)
            win.transient(self.root)
            win.grab_set()
            win.resizable(False, False)

            # Message
            frm = tk.Frame(win, padx=16, pady=12)
            frm.pack(fill=tk.BOTH, expand=True)
            lbl = tk.Label(frm, text=message, justify=tk.LEFT, anchor="w")
            lbl.pack(fill=tk.BOTH, expand=True)

            # Buttons row
            btn_row = tk.Frame(frm)
            btn_row.pack(fill=tk.X, pady=(12, 0))

            def _choose(val):
                result["choice"] = val
                try:
                    win.grab_release()
                except Exception:
                    pass
                win.destroy()
                done.set()

            # Exit (left), Continue (middle), Level up (right)
            tk.Button(btn_row, text="Exit", width=12, command=lambda: _choose("exit")).pack(side=tk.LEFT, padx=4)
            tk.Button(btn_row, text="Continue", width=14, command=lambda: _choose("continue")).pack(side=tk.LEFT, padx=4)
            tk.Button(btn_row, text="Level up", width=12, command=lambda: _choose("level_up")).pack(side=tk.RIGHT, padx=4)

            # Handle window close (treat as Exit)
            win.protocol("WM_DELETE_WINDOW", lambda: _choose("exit"))

            # Center relative to root
            try:
                win.update_idletasks()
                rx = self.root.winfo_rootx()
                ry = self.root.winfo_rooty()
                rw = self.root.winfo_width()
                rh = self.root.winfo_height()
                ww = win.winfo_width()
                wh = win.winfo_height()
                x = rx + max(0, (rw - ww) // 2)
                y = ry + max(0, (rh - wh) // 2)
                win.geometry("+" + str(x) + "+" + str(y))
            except Exception:
                pass

        self.root.after(0, _show_dialog)
        done.wait()
        return result.get("choice", "continue")

    def _load_level_thresholds(self):
        """Parse constants.txt for lines like 'max_level_ball01 = 5' and return dict { 'ball01': 5, ... }"""
        mapping = {}
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(here, "constants.txt")
            if not os.path.exists(path):
                return mapping
            with open(path, "r") as f:
                for line in f:
                    m = re.match(r"\s*max_level_(ball[_ ]?0?[1-4])\s*=\s*(\d+)\s*", line, re.IGNORECASE)
                    if m:
                        raw_lvl = m.group(1)
                        lvl = self._normalize_level_name(raw_lvl)
                        val = int(m.group(2))
                        mapping[lvl] = val
        except Exception as e:
            print("Failed to load constants.txt:", e)
        return mapping

    def _normalize_level_name(self, name):
        """Normalize variants like 'ball_01', 'ball 01', 'ball1' to 'ball01'."""
        try:
            if not isinstance(name, str):
                return name
            s = name.strip().lower().replace(" ", "").replace("_", "")
            # Expect formats like ball01 or ball1
            m = re.match(r"^ball0?([1-4])$", s)
            if m:
                n = int(m.group(1))
                return "ball0" + str(n)
            return name
        except Exception:
            return name

    def _get_next_level(self, level_name):
        """Given 'ball01'..'ball04' (or variants), return the next normalized level string or None if at top."""
        try:
            norm = self._normalize_level_name(level_name)
            m = re.match(r"^ball0([1-4])$", norm)
            if not m:
                return None
            n = int(m.group(1))
            if n >= 4:
                return None
            nxt = n + 1
            return "ball0" + str(nxt)
        except Exception:
            return None

    def _resolve_game_script_path(self, script_name):
        """Return an absolute path to the given script, relative to this file's directory."""
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            candidate = os.path.join(here, script_name)
            return candidate
        except Exception:
            return script_name

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

'''
Look at constants.txt. The max score required for the player to be able to move to the next level is set in this file, 
in the form of max_level_ball0n = 5 where n is the number related to the current level.
'''