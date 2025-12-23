import os
import tempfile
import yaml

import run


def write_players_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def read_players_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_high_score_updates_only_when_higher(monkeypatch):
    players = {
        "David": {
            "high_scores": {
                "ball01": 5
            }
        }
    }

    with tempfile.TemporaryDirectory() as tmp:
        yaml_path = os.path.join(tmp, "players.yaml")
        write_players_yaml(yaml_path, players)

        # Force run.py to read our temp file instead of real one
        monkeypatch.setattr(
            run,
            "os",
            type("OS", (), {
                "path": os.path,
                "getcwd": lambda: tmp,
                "exists": os.path.exists
            })
        )

        # Lower score → no update
        run.update_player_high_score("ball01", "David", 3)
        data = read_players_yaml(yaml_path)
        assert data["David"]["high_scores"]["ball01"] == 5

        # Higher score → update
        run.update_player_high_score("ball01", "David", 8)
        data = read_players_yaml(yaml_path)
        assert data["David"]["high_scores"]["ball01"] == 8


def test_missing_player_is_safe(monkeypatch):
    players = {}

    with tempfile.TemporaryDirectory() as tmp:
        yaml_path = os.path.join(tmp, "players.yaml")
        write_players_yaml(yaml_path, players)

        monkeypatch.setattr(
            run,
            "os",
            type("OS", (), {
                "path": os.path,
                "getcwd": lambda: tmp,
                "exists": os.path.exists
            })
        )

        # Should not crash
        run.update_player_high_score("ball01", "Nobody", 10)

        data = read_players_yaml(yaml_path)
        assert data == {}