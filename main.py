import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import os
import subprocess
import sys

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

class AngryGrannyApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        self.players = load_players()
        create_default_admin(self.players)
        self.selected_player = None
        self.splash_screen()

    def splash_screen(self):
        splash = tk.Toplevel()
        splash.geometry("400x150")
        splash.title("Loading")
        label = tk.Label(splash, text="Welcome to Angry Granny!", font=("Arial", 20))
        label.pack(expand=True)
        splash.after(000, lambda: (splash.destroy(), self.show_main_window()))

    def show_main_window(self):
        self.root.deiconify()
        self.root.title("Angry Granny")
        self.root.geometry("400x400")

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
        if self.selected_player:
            level = self.players[self.selected_player]["current_level"]
            messagebox.showinfo("Player Info", f"Player: {self.selected_player}\nLevel: {level}")
            try:
                subprocess.Popen([sys.executable, "angry_granny_py5.py", self.selected_player, level])
            except Exception as e:
                messagebox.showerror("Launch Error", f"Could not launch game:\n{e}")

    def add_new_player(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add Player")
        popup.geometry("300x250")

        tk.Label(popup, text="Nickname").pack()
        nickname_entry = tk.Entry(popup)
        nickname_entry.pack()

        tk.Label(popup, text="Email").pack()
        email_entry = tk.Entry(popup)
        email_entry.pack()

        tk.Label(popup, text="Password").pack()
        password_entry = tk.Entry(popup, show="*")
        password_entry.pack()

        tk.Label(popup, text="Start Level").pack()
        level_var = tk.StringVar(popup)
        level_var.set(LEVELS[0])
        level_menu = tk.OptionMenu(popup, level_var, *LEVELS)
        level_menu.pack()

        def submit():
            nick = nickname_entry.get().strip()
            email = email_entry.get().strip()
            password = password_entry.get()
            level = level_var.get()

            if not nick or not email or not password:
                messagebox.showerror("Error", "All fields required")
                return

            if "@" not in email:
                messagebox.showerror("Error", "Invalid email")
                return

            if nick in self.players:
                messagebox.showerror("Error", "Nickname already exists")
                return

            self.players[nick] = {
                "email": email,
                "password": password,
                "current_level": level,
                "high_scores": {lvl: 0 for lvl in LEVELS},
                "is_admin": False
            }
            save_players(self.players)
            popup.destroy()
            self.update_player_list()
            self.selected_player = nick
            self.select_player_in_list(nick)

        tk.Button(popup, text="Submit", command=submit).pack(pady=10)

    def select_player_in_list(self, nick):
        index = list(self.players.keys()).index(nick)
        self.listbox.select_set(index)
        self.listbox.event_generate("<<ListboxSelect>>")

    def delete_player(self):
        if not self.selected_player:
            messagebox.showwarning("No player selected", "Select a player to delete.")
            return

        player = self.players[self.selected_player]
        if player["is_admin"]:
            messagebox.showwarning("Permission denied", "Admin cannot be deleted.")
            return

        pw = simpledialog.askstring("Confirm Delete", f"Enter password to delete {self.selected_player}:", show="*")
        if pw == player["password"]:
            del self.players[self.selected_player]
            save_players(self.players)
            messagebox.showinfo("Deleted", f"{self.selected_player} has been deleted.")
            self.selected_player = None
            self.play_button.config(state=tk.DISABLED)
            self.update_player_list()
        else:
            messagebox.showerror("Incorrect Password", "Password incorrect.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AngryGrannyApp(root)
    root.mainloop()