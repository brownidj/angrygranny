import json
import os
import sys

from PySide6.QtCore import QFile
from PySide6.QtCore import QLibraryInfo
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QWidget, QPushButton
from PySide6.QtWidgets import QListWidget, QLineEdit


def apply_styles(app):
    # Load shared stylesheet angry_granny.qss if present
    qss_file = QFile("angry_granny.qss")
    if qss_file.exists() and qss_file.open(QFile.ReadOnly):
        try:
            app.setStyleSheet(bytes(qss_file.readAll()).decode())
        finally:
            qss_file.close()


def load_players_index():
    """
    Load players from players.json and return:
      - index: dict mapping player name -> record dict (may be empty dict)
      - names: list of names in a stable order
    Supports shapes:
      * {"players": [{"name": "Alice", ...}, ...]}
      * {"players": {"Alice": {...}, ...}}
      * [{"name": "Alice", ...}, ...]
      * {"Alice": {...}, "Bob": {...}}
      * {"players": ["Alice", "Bob", ...]} or ["Alice", "Bob", ...]
    """
    candidates = [
        os.path.join(os.getcwd(), "players.json"),
        os.path.join(os.getcwd(), "data", "players.json"),
    ]
    data = None
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                break
            except Exception as e:
                print("Warning: failed to load " + path + ": " + str(e))
                return {}, []
    if data is None:
        print("Warning: players.json not found in project root or data/")
        return {}, []

    index = {}
    names = []

    def add_name_record(name, rec):
        if isinstance(name, str) and name:
            if name not in index:
                index[name] = rec if isinstance(rec, dict) else {}
                names.append(name)

    if isinstance(data, dict):
        if "players" in data:
            players = data["players"]
            if isinstance(players, dict):
                for name, rec in players.items():
                    add_name_record(name, rec)
            elif isinstance(players, list):
                for item in players:
                    if isinstance(item, str):
                        add_name_record(item, {})
                    elif isinstance(item, dict):
                        nm = item.get("name")
                        add_name_record(nm, item)
            else:
                pass
        else:
            # dict keyed by player names
            for name, rec in data.items():
                add_name_record(name, rec)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                add_name_record(item, {})
            elif isinstance(item, dict):
                nm = item.get("name")
                add_name_record(nm, item)
    return index, names


def update_selected_player_level_edit(window):
    lst = window.findChild(QListWidget, "listPlayers")
    level_edit = window.findChild(QLineEdit, "editLevel")
    if not lst or not level_edit:
        print("Warning: listPlayers or editLevel widget not found in main_portrait.ui")
        return
    item = lst.currentItem()
    if item is None:
        level_edit.clear()
        return
    name = item.text()
    idx, _ = load_players_index()
    rec = idx.get(name)
    lvl = None
    if isinstance(rec, dict):
        for key in ("current_level", "level", "currentLevel"):
            if key in rec:
                lvl = rec[key]
                break
    level_edit.setText("" if lvl is None else str(lvl))


def populate_players_list(window):
    _, names = load_players_index()
    lst = window.findChild(QListWidget, "listPlayers")
    if not lst:
        print("Warning: listPlayers widget not found in main_portrait.ui")
        return
    lst.clear()
    if names:
        lst.addItems(names)
    # (Re)connect selection change to update the label
    try:
        lst.itemSelectionChanged.disconnect()
    except Exception:
        pass
    lst.itemSelectionChanged.connect(lambda: update_selected_player_level_edit(window))
    # Select first row if available and update label immediately
    if lst.count() > 0:
        lst.setCurrentRow(0)
    update_selected_player_level_edit(window)


# Force Qt to the correct plugin folders
plugins = QLibraryInfo.path(QLibraryInfo.PluginsPath)
if plugins:
    os.environ.setdefault("QT_PLUGIN_PATH", plugins)
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", os.path.join(plugins, "platforms"))


def open_main_portrait_from_splash(splash):
    loader = QUiLoader()
    ui_file = QFile("ui/main_portrait.ui")
    if not ui_file.open(QFile.ReadOnly):
        print("Error: could not open ui/main_portrait.ui")
        return
    main_window = loader.load(ui_file)
    ui_file.close()
    if not isinstance(main_window, QWidget):
        print("Error: main_portrait.ui did not load correctly.")
        return
    populate_players_list(main_window)
    # Keep a reference so it is not garbage collected
    splash._main_window = main_window
    main_window.show()
    splash.close()


def make_splash_screen(loader: QUiLoader) -> QWidget:
    splash_file = QFile("ui/splash_portrait.ui")
    if not splash_file.open(QFile.ReadOnly):
        print("Error: could not open ui/splash_portrait.ui")
        sys.exit(1)
    splash = loader.load(splash_file)
    splash_file.close()

    if not isinstance(splash, QWidget):
        print("Error: splash_portrait.ui did not load correctly.")
        sys.exit(1)

    btn = splash.findChild(QPushButton, "btnLetsPlay")
    if btn is None:
        print("Warning: btnLetsPlay button not found in splash_portrait.ui")
    else:
        btn.clicked.connect(lambda: open_main_portrait_from_splash(splash))
    return splash


def main():
    app = QApplication(sys.argv)
    apply_styles(app)
    loader = QUiLoader()

    splash = make_splash_screen(loader)
    splash.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
