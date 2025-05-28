import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog

DATA_FILE = "players.json"
LEVELS = ["Easy", "Medium", "Hard"]


def load_players():
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_players(players):
    with open(DATA_FILE, "w") as f:
        json.dump(players, f, indent=2)


def create_default_admin(players):
    if not any(p["is_admin"] for p in players.values()):
        players["AdminGranny"] = {
            "email": "admin@granny.com",
            "password": "admin123",
            "current_level": "Easy",
            "high_scores": {lvl: 0 for lvl in LEVELS},
            "is_admin": True
        }
        save_players(players)


# Assumes load_players, save_players, create_default_admin are defined elsewhere
class AngryGrannyApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        self.players = load_players()
        create_default_admin(self.players)
        self.selected_player = None
        self.sound_on = True  # default sound setting
        self.splash_screen()

    def show_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Settings")
        dlg.geometry("300x150")
        # Sound on/off setting
        sound_var = tk.BooleanVar(value=self.sound_on)
        tk.Checkbutton(dlg, text="Sound On", variable=sound_var).pack(padx=10, pady=10)
        def apply_and_close():
            self.sound_on = sound_var.get()
            dlg.destroy()
        tk.Button(dlg, text="OK", command=apply_and_close).pack(pady=(0,10))

    def splash_screen(self):
        splash = tk.Toplevel()
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

        # --- Toolbar with settings icon ---
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        settings_icon = tk.Label(toolbar, text="⚙", font=("Arial", 48))
        settings_icon.pack(side=tk.RIGHT, padx=8, pady=4)
        settings_icon.bind("<Button-1>", lambda e: self.show_settings())

        # --- Player list and controls ---
        self.listbox = tk.Listbox(self.root, height=10, width=40)
        self.listbox.pack(pady=10)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        self.play_button = tk.Button(self.root, text="Play", command=self.play_game, state=tk.DISABLED)
        self.play_button.pack(pady=5)
        tk.Button(self.root, text="Add New Player", command=self.add_new_player).pack(pady=5)
        tk.Button(self.root, text="Delete Player", command=self.delete_player).pack(pady=5)

        self.update_player_list()

    def update_player_list(self):
        self.listbox.delete(0, tk.END)
        for nick in self.players.keys():
            self.listbox.insert(tk.END, nick)

    def on_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            self.selected_player = self.listbox.get(selection[0])
            self.play_button.config(state=tk.NORMAL)

    def play_game(self):
        if not self.selected_player:
            return
        player = self.selected_player
        level = self.players[player]["current_level"]

        def run_game_and_update(player, level):
            try:
                while True:
                    print(f"Launching game for {player} at {level}...")
                    args = [sys.executable, "angry_granny_py5.py", player, level]
                    if not self.sound_on:
                        args.append("--mute")
                    proc = subprocess.Popen(args)
                    proc.wait()
                    print("Game subprocess ended.")

                    result_file = "last_score.json"
                    if os.path.exists(result_file):
                        with open(result_file, "r") as f:
                            res = json.load(f)
                        score = res.get("score", 0)
                        current_high = self.players[player]["high_scores"].get(level, 0)
                        msg = f"{player} scored {score} on {level}.\n"
                        if score > current_high:
                            self.players[player]["high_scores"][level] = score
                            save_players(self.players)
                            msg += "🎉 Congratulations! A new high score has been recorded!"
                        else:
                            msg += f"Current high score: {current_high}."
                        os.remove(result_file)
                    else:
                        msg = "Game finished but no improved score was recorded."
                    msg += "\n\nPlay again?"
                    again = messagebox.askyesno("Game Over", msg)
                    if not again:
                        break
                    time.sleep(1)
            except Exception as e:
                print("Exception in game thread:", repr(e))
                err_msg = f"Could not launch game:\n{e}"
                self.root.after(0, lambda: messagebox.showerror("Launch Error", err_msg))

        threading.Thread(target=run_game_and_update, args=(player, level), daemon=True).start()

    def add_new_player(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add Player")
        popup.geometry("300x250")
        tk.Label(popup, text="Nickname").pack()
        nick_entry = tk.Entry(popup); nick_entry.pack()
        tk.Label(popup, text="Email").pack()
        email_entry = tk.Entry(popup); email_entry.pack()
        tk.Label(popup, text="Password").pack()
        pw_entry = tk.Entry(popup, show="*"); pw_entry.pack()
        tk.Label(popup, text="Start Level").pack()
        lvl_var = tk.StringVar(popup); lvl_var.set(LEVELS[0])
        tk.OptionMenu(popup, lvl_var, *LEVELS).pack()
        def submit():
            nick = nick_entry.get().strip()
            email = email_entry.get().strip()
            pw = pw_entry.get()
            lvl = lvl_var.get()
            if not nick or not email or not pw:
                messagebox.showerror("Error", "All fields required")
                return
            if "@" not in email:
                messagebox.showerror("Error", "Invalid email")
                return
            if nick in self.players:
                messagebox.showerror("Error", "Nickname exists")
                return
            self.players[nick] = {"email": email, "password": pw, "current_level": lvl,
                                   "high_scores": {lvl: 0 for lvl in LEVELS}, "is_admin": False}
            save_players(self.players)
            popup.destroy(); self.update_player_list()
            self.select_player_in_list(nick)
        tk.Button(popup, text="Submit", command=submit).pack(pady=10)

    def select_player_in_list(self, nick):
        idx = list(self.players.keys()).index(nick)
        self.listbox.select_set(idx)
        self.listbox.event_generate("<<ListboxSelect>>")

    def delete_player(self):
        if not self.selected_player:
            messagebox.showwarning("No player selected", "Select a player to delete.")
            return
        player = self.players[self.selected_player]
        if player.get("is_admin"):
            messagebox.showwarning("Permission denied", "Cannot delete admin.")
            return
        pw = simpledialog.askstring("Confirm Delete", f"Enter password to delete {self.selected_player}:", show="*")
        if pw == player.get("password"):
            del self.players[self.selected_player]
            save_players(self.players)
            messagebox.showinfo("Deleted", f"{self.selected_player} deleted.")
            self.selected_player = None
            self.play_button.config(state=tk.DISABLED)
            self.update_player_list()
        else:
            messagebox.showerror("Incorrect Password", "Password incorrect.")


if __name__ == "__main__":
    root = tk.Tk()
    app = AngryGrannyApp(root)
    root.mainloop()
