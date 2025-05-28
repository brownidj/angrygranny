import os
import sys
import subprocess
import time
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import json

from settings_dialog import SettingsDialog
from player_manager import PlayerManager
from game_launcher import GameLauncher
from players_ui import PlayerPanel

DATA_FILE = "players.json"
LEVELS = ["Easy", "Medium", "Hard"]

class AngryGrannyApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()

        # Initialize PlayerManager
        # Resolve data file path relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(script_dir, DATA_FILE)
        self.pm = PlayerManager(data_file=data_path, levels=LEVELS)
        self.players = self.pm.players

        self.selected_player = None
        self.sound_on = True  # default sound setting

        # Load settings icon
        self.settings_img = None
        try:
            img_path = os.path.join(script_dir, "assets", "settings.jpg")
            img = Image.open(img_path)
            img = img.resize((24, 24), Image.LANCZOS)
            self.settings_img = ImageTk.PhotoImage(img)
        except Exception as e:
            print("Failed to load settings icon:", e)

        self.splash_screen()

    def show_settings(self):
        dlg = SettingsDialog(self.root, self.sound_on)
        self.sound_on = dlg.show()

    def splash_screen(self):
        splash = tk.Toplevel(self.root)
        splash.geometry("400x150")
        splash.title("Waiting")
        tk.Label(splash, text="Welcome to Angry Granny!", font=("Arial", 20)).pack(expand=True)
        def close_splash():
            splash.destroy()
            self.root.after(50, self.show_main_window)
        splash.after(2000, close_splash)

    def show_main_window(self):
        self.root.deiconify()
        self.root.title("Angry Granny")
        self.root.geometry("400x400")

        # Toolbar with settings icon
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        if self.settings_img:
            btn = tk.Label(toolbar, image=self.settings_img)
        else:
            btn = tk.Label(toolbar, text="⚙", font=("Arial", 24))
        btn.pack(side=tk.RIGHT, padx=8, pady=4)
        btn.bind("<Button-1>", lambda e: self.show_settings())

        # Player panel
        self.player_panel = PlayerPanel(self.root, self.pm)
        self.player_panel.pack(pady=10)
        # Bind selection event without overriding the panel's own handler
        self.player_panel.listbox.bind("<<ListboxSelect>>", self.on_player_select, add="+")

        # Controls
        self.play_button = tk.Button(self.root, text="Play", command=self.play_game, state=tk.DISABLED)
        self.play_button.pack(pady=5)

    def on_player_select(self, event=None):
        player = self.player_panel.selected
        if player:
            self.play_button.config(state=tk.NORMAL)
        else:
            self.play_button.config(state=tk.DISABLED)

    def play_game(self):
        player = self.player_panel.selected
        if not player:
            return
        level = self.pm.players[player]["current_level"]
        launcher = GameLauncher(self.root, self.pm, self.sound_on)
        launcher.run(player, level)

if __name__ == "__main__":
    root = tk.Tk()
    app = AngryGrannyApp(root)
    root.mainloop()