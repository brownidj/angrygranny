import json
import os

class PlayerManager:
    """
    Handles loading, saving, and manipulating player data stored in a JSON file.
    """
    def __init__(self, data_file="players.json", levels=None):
        self.data_file = data_file
        self.levels    = levels or []
        self.players   = {}
        self.load()

    def load(self):
        if os.path.exists(self.data_file) and os.path.getsize(self.data_file) > 0:
            with open(self.data_file, "r") as file:
                self.players = json.load(file)
                # print(self.players)
                for player in self.players:
                    print(f'{player} {self.players[player]}')
        else:
            self.players = {}
        self.create_default_admin()

    def save(self):
        with open(self.data_file, "w") as file:
            json.dump(self.players, file, indent=2)

    """
    Check to see if there is an admin; if not create one
    """
    def create_default_admin(self):
        if not any(p.get("is_admin") for p in self.players.values()):
            self.players["AdminGranny"] = {
                "email": "admin@granny.com",
                "password": "admin123",
                "current_level": "Easy",
                "high_scores": {lvl: 0 for lvl in self.levels},
                "is_admin": True
            }
            self.save()

    def get_nicks(self):
        return list(self.players.keys())

    def add_player(self, nick, email, password, level):
        if nick in self.players:
            raise ValueError("Nickname already exists")
        self.players[nick] = {
            "email": email,
            "password": password,
            "current_level": level,
            "high_scores": {lvl: 0 for lvl in self.levels},
            "is_admin": False
        }
        self.save()

    def delete_player(self, nick, password):
        player = self.players.get(nick)
        if not player:
            raise KeyError("Player not found")
        if player.get("is_admin"):
            raise PermissionError("Cannot delete admin")
        if player.get("password") != password:
            raise PermissionError("Incorrect password")
        del self.players[nick]
        self.save()

    def get_high_score(self, nick, level):
        return self.players.get(nick, {}).get("high_scores", {}).get(level, 0)

    def set_high_score(self, nick, level, score):
        if nick in self.players:
            self.players[nick]["high_scores"][level] = score
            self.save()