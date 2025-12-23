

def update_player_high_score(level_code: str, player_name: str, score: int, landscape_window: "QWidget | None" = None):
    """Update the high score for a player/level in players.yaml if the new score is higher.

    If landscape_window is provided, refresh the High Scores table for that level
    and repopulate the portrait Players list.
    """
    if not level_code or not player_name:
        print(f"[DEBUG] Skipping update_player_high_score: missing level or player (level={level_code!r}, player={player_name!r})")
        return

    candidates = [
        os.path.join(os.getcwd(), "data", "players.yaml"),
        os.path.join(os.getcwd(), "players.yaml"),
    ]
    path = None
    data = None
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                path = p
                break
            except Exception as e:
                print("Warning: failed to read players file", p, ":", str(e))
                return

    if path is None or data is None:
        print("Warning: players.yaml not found; cannot update high score")
        return

    # Locate the players dictionary inside the loaded structure
    players_dict = None
    if isinstance(data, dict):
        if "players" in data and isinstance(data["players"], dict):
            players_dict = data["players"]
        else:
            players_dict = data
    else:
        print("Warning: players.yaml format not understood for high score update")
        return

    rec = players_dict.get(player_name)
    if not isinstance(rec, dict):
        print(f"Warning: no record found for player {player_name!r} in players.yaml")
        return

    hs = rec.get("high_scores")
    if not isinstance(hs, dict):
        hs = {}
        rec["high_scores"] = hs

    old_val = hs.get(level_code, 0)
    if not isinstance(old_val, (int, float)):
        old_val = 0

    if score <= old_val:
        print(f"[DEBUG] Not updating high score for {player_name!r} at {level_code!r}: {score} <= {old_val}")
        return

    hs[level_code] = int(score)
    print(f"[DEBUG] Updated high score for {player_name!r} at {level_code!r}: {old_val} -> {score}")

    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
    except Exception as e:
        print("Warning: failed to write players.yaml:", str(e))
        return

    # Refresh UI if a landscape_window is provided
    if landscape_window is not None:
        try:
            populate_high_scores_for_level(landscape_window)
        except Exception as e:
            print("Warning: failed to refresh high scores table:", str(e))

        portrait = getattr(landscape_window, "_portrait_window", None)
        if isinstance(portrait, QWidget):
            try:
                populate_players_list(portrait)
            except Exception as e:
                print("Warning: failed to refresh players list:", str(e))

import json
import os
import sys
import yaml

# --- Levels configuration (replaces constants.txt) ------------------------

_LEVELS_CONFIG = None

def load_levels_config() -> dict:
    """Load and cache data/levels.yaml.

    Expected shape:
      {"levels": {"ball01": {"full_label": ..., "short_label": ..., "duration": ..., "level_up_target": ...}, ...}}
    """
    global _LEVELS_CONFIG
    if isinstance(_LEVELS_CONFIG, dict):
        return _LEVELS_CONFIG

    # Resolve levels.yaml relative to this file, not the current working directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "data", "levels.yaml")
    if not os.path.exists(path):
        print("Warning: data/levels.yaml not found; using empty levels config")
        _LEVELS_CONFIG = {"levels": {}}
        return _LEVELS_CONFIG

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print("Warning: failed to read data/levels.yaml:", str(e))
        data = None

    if not isinstance(data, dict) or not isinstance(data.get("levels"), dict):
        print("Warning: data/levels.yaml has unexpected format; using empty levels config")
        _LEVELS_CONFIG = {"levels": {}}
        return _LEVELS_CONFIG

    _LEVELS_CONFIG = data
    return _LEVELS_CONFIG


def _levels_map() -> dict:
    cfg = load_levels_config()
    return cfg.get("levels", {}) if isinstance(cfg, dict) else {}

# Helper to set is_current_player flag in players.yaml
def set_current_player_flag(selected_name: str):
    """
    Update data/players.yaml so that only the selected player has
    is_current_player: true, and all others are set to false.
    """
    path = os.path.join(os.getcwd(), "data", "players.yaml")
    if not os.path.exists(path):
        print("Warning: data/players.yaml not found")
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print("Warning: failed to read players.yaml:", str(e))
        return

    if not isinstance(data, dict):
        print("Warning: players.yaml format not understood")
        return

    for name, rec in data.items():
        if isinstance(rec, dict):
            rec["is_current_player"] = (name == selected_name)

    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
    except Exception as e:
        print("Warning: failed to write players.yaml:", str(e))

from PySide6.QtCore import QFile, Qt, QLibraryInfo, QPropertyAnimation
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtGui import QPixmap
from game_widget import GameWidget
from game_state import Ball01Rules, Ball02Rules, Ball03Rules, Ball04Rules


def get_level_label(level_code: str) -> str:
    """Return the full, friendly label for a level code (e.g. 'Tea with Granny')."""
    if not level_code:
        return ""
    key = str(level_code).lower()
    rec = _levels_map().get(key)
    if isinstance(rec, dict):
        val = rec.get("full_label")
        if isinstance(val, str):
            return val
    # Fallback to raw code if unknown
    return str(level_code)


# Helper to get the short label for a level code
def get_level_short_label(level_code: str) -> str:
    """Return the short label for a level code (e.g. 'Tea')."""
    if not level_code:
        return ""
    key = str(level_code).lower()
    rec = _levels_map().get(key)
    if isinstance(rec, dict):
        val = rec.get("short_label")
        if isinstance(val, str):
            return val
    # Fallback to full label or raw
    full = get_level_label(level_code)
    return full if full else str(level_code)


def get_level_duration(level_code: str, default_seconds: int = 20) -> int:
    """Return the round duration for a level code in seconds."""
    if not level_code:
        return int(default_seconds)
    key = str(level_code).lower()
    rec = _levels_map().get(key)
    if isinstance(rec, dict):
        val = rec.get("duration")
        if isinstance(val, (int, float)):
            return int(val)
    return int(default_seconds)


def get_level_up_target(level_code: str, default_target: int = 3) -> int:
    """Return the level-up target threshold for a level code."""
    if not level_code:
        return int(default_target)
    key = str(level_code).lower()
    rec = _levels_map().get(key)
    if isinstance(rec, dict):
        val = rec.get("level_up_target")
        if isinstance(val, (int, float)):
            return int(val)
    return int(default_target)



def apply_styles(app):
    # Load shared stylesheet angry_granny.qss if present
    qss_file = QFile("angry_granny.qss")
    if qss_file.exists() and qss_file.open(QFile.ReadOnly):
        try:
            app.setStyleSheet(bytes(qss_file.readAll()).decode())
        finally:
            qss_file.close()


# --- Toast helper ----------------------------------------------------------

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel

def show_toast(parent, message: str, duration_ms: int = 2000):
    """
    Show a temporary toast-style message inside the given parent window.
    """
    toast = QLabel(parent)
    toast.setText(message)
    toast.setStyleSheet(
        "background-color: rgba(0, 0, 0, 180);"
        "color: white;"
        "padding: 8px 14px;"
        "border-radius: 8px;"
        "font-size: 14pt;"
    )
    toast.setAlignment(Qt.AlignCenter)
    toast.setAttribute(Qt.WA_TransparentForMouseEvents)

    toast.adjustSize()
    pw = parent.width()
    ph = parent.height()
    tw = toast.width()
    th = toast.height()

    toast.move(pw // 2 - tw // 2, ph - th - 40)
    toast.show()

    QTimer.singleShot(duration_ms, toast.close)


def load_players_index():
    """
    Load players from data/players.yaml and return:
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
        os.path.join(os.getcwd(), "data", "players.yaml"),
        os.path.join(os.getcwd(), "players.yaml"),
    ]
    data = None
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                break
            except Exception as e:
                print("Warning: failed to load " + path + ": " + str(e))
                return {}, []
    if data is None:
        print("Warning: players.yaml not found in data/ or project root")
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


def update_selected_player_details(window):
    table = window.findChild(QTableWidget, "listPlayers")
    if not table:
        print("Warning: listPlayers (QTableWidget) not found in main_portrait.ui")
        return

    name_edit = window.findChild(QLineEdit, "editName")
    # Other detail widgets are optional; we will find them if present
    spin_age = window.findChild(QWidget, "spinAge")
    date_last = window.findChild(QWidget, "dateLastPlayed")
    notes_edit = window.findChild(QWidget, "editNotes")

    row = table.currentRow()
    if row < 0:
        if name_edit:
            name_edit.clear()
        return

    item = table.item(row, 0)
    if item is None:
        return

    name = item.text()
    set_current_player_flag(name)
    idx, _ = load_players_index()
    rec = idx.get(name) or {}

    # Update name
    if name_edit is not None:
        name_edit.setText(name)

    # Optional extras if the widgets and data exist
    if isinstance(rec, dict):
        # Age
        if spin_age is not None and hasattr(spin_age, "setValue"):
            age = rec.get("age")
            if isinstance(age, int):
                spin_age.setValue(age)
        # Last played date (expects ISO "YYYY-MM-DD")
        if date_last is not None and hasattr(date_last, "setDate"):
            lp = rec.get("last_played")
            try:
                from PySide6.QtCore import QDate
                if isinstance(lp, str) and len(lp) >= 10:
                    year = int(lp[0:4])
                    month = int(lp[5:7])
                    day = int(lp[8:10])
                    date_last.setDate(QDate(year, month, day))
            except Exception:
                pass
        # Notes
        if notes_edit is not None and hasattr(notes_edit, "setPlainText"):
            notes = rec.get("notes")
            if isinstance(notes, str):
                notes_edit.setPlainText(notes)

    # Enable Play button when a player is selected
    btn_play = window.findChild(QPushButton, "btnPlay")
    if btn_play is not None:
        btn_play.setEnabled(True)


def populate_players_list(window, filter_text: str = ""):
    idx, names = load_players_index()
    # Apply optional case-insensitive name filter (search only by player name)
    ft = (filter_text or "").strip().lower()
    if ft:
        names = [n for n in names if ft in n.lower()]
    table = window.findChild(QTableWidget, "listPlayers")
    if not table:
        print("Warning: listPlayers (QTableWidget) not found in main_portrait.ui")
        return
    # Ensure full-row selection so selected row uses QSS highlight (white on blue)
    from PySide6.QtWidgets import QAbstractItemView
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)

    table.clearContents()
    table.setRowCount(len(names))

    row = 0
    current_player_name = None
    for name in names:
        rec = idx.get(name) or {}
        if isinstance(rec, dict) and rec.get("is_current_player") is True:
            current_player_name = name

        # Determine the current level for this player
        current_level = None
        if isinstance(rec, dict):
            for key in ("current_level", "level", "currentLevel"):
                if key in rec:
                    current_level = rec[key]
                    break

        # Score shown is the score for the current level, if available
        score = None
        if isinstance(rec, dict):
            hs_map = rec.get("high_scores", {})
            if isinstance(hs_map, dict) and current_level:
                val = hs_map.get(current_level)
                if isinstance(val, (int, float)) and val > 0:
                    score = val

        name_item = QTableWidgetItem(name)
        score_item = QTableWidgetItem("" if score is None else str(score))
        score_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        table.setItem(row, 0, name_item)
        table.setItem(row, 1, score_item)
        # Show a short, friendly label in the Level column but keep the raw code as user data
        if current_level is None:
            level_text = ""
        else:
            level_text = get_level_short_label(current_level)
        level_item = QTableWidgetItem(level_text)
        if current_level:
            level_item.setData(Qt.UserRole, str(current_level))
        table.setItem(row, 2, level_item)
        row = row + 1

    table.setSortingEnabled(True)
    header = table.horizontalHeader()
    header.setSectionsClickable(True)
    header.setSortIndicatorShown(True)
    table.sortItems(0)  # sort by player name column

    # Connect selection change to detail updater
    # Only connect once per table instance to avoid duplicate calls and warnings.
    if not hasattr(table, "_selection_connected"):
        table.itemSelectionChanged.connect(lambda: update_selected_player_details(window))
        table._selection_connected = True

    # If there's exactly one visible player after filtering, auto-select it
    ft = (filter_text or "").strip().lower()
    if table.rowCount() == 1 and ft:
        table.setCurrentCell(0, 0)
        table.setFocus()
        table.repaint()
        update_selected_player_details(window)
        return

    # Select the current player row if flagged; otherwise leave nothing selected
    if table.rowCount() > 0 and current_player_name:
        target_row = 0
        for r in range(table.rowCount()):
            item = table.item(r, 0)
            if item is not None and item.text() == current_player_name:
                target_row = r
                break
        table.setCurrentCell(target_row, 0)
        table.setFocus()
        table.repaint()
        # Ensure the selected row is visible (e.g. for long player lists)
        selected_item = table.item(target_row, 0)
        if selected_item is not None:
            table.scrollToItem(selected_item)
        update_selected_player_details(window)
    else:
        # No current player flagged or visible under this filter: disable Play
        btn_play = window.findChild(QPushButton, "btnPlay")
        if btn_play is not None:
            btn_play.setEnabled(False)
        # Only show the toast when there is no active filter (initial state)
        ft = (filter_text or "").strip()
        if not ft:
            print("[DEBUG] No current player flagged; Play disabled, showing toast")
            show_toast(window, "Select a player")

    # Final safeguard: ensure Play is enabled if and only if a row is selected
    btn_play = window.findChild(QPushButton, "btnPlay")
    if btn_play is not None:
        has_selection = table.currentRow() >= 0
        btn_play.setEnabled(has_selection)


# Force Qt to the correct plugin folders
plugins = QLibraryInfo.path(QLibraryInfo.PluginsPath)
if plugins:
    os.environ.setdefault("QT_PLUGIN_PATH", plugins)
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", os.path.join(plugins, "platforms"))


def exit_with_fade(main_window: QWidget):
    """
    Show a sad granny image inside the main window and fade it out
    over 5 seconds, then quit the application cleanly.
    """
    print(f"[DEBUG] exit_with_fade called on {main_window.objectName()}")
    app = QApplication.instance()
    if app is None:
        main_window.close()
        sys.exit(0)

    # Hide all existing child widgets in the main window before showing the fade animation
    for child in main_window.findChildren(QWidget):
        if child is not main_window:
            child.hide()

    # Create an overlay widget as a child of the main window
    overlay = QWidget(main_window)
    overlay.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
    overlay.setAttribute(Qt.WA_TranslucentBackground, True)
    overlay.setGeometry(main_window.rect())

    layout = QVBoxLayout(overlay)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    label = QLabel()
    label.setAlignment(Qt.AlignCenter)
    pixmap = QPixmap(os.path.join("assets", "sad_granny.png"))
    if not pixmap.isNull():
        print(f"[DEBUG] sad_granny.png loaded, original size={pixmap.size()}")
        # Scale to fit within 80% of the main window, keeping aspect ratio
        target_width = int(main_window.width() * 0.8)
        target_height = int(main_window.height() * 0.8)
        scaled = pixmap.scaled(target_width, target_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)
    else:
        print("[DEBUG] ERROR: sad_granny.png failed to load!")
    layout.addWidget(label)

    overlay.show()

    # Apply an opacity effect so we can fade the overlay inside the window
    effect = QGraphicsOpacityEffect(overlay)
    overlay.setGraphicsEffect(effect)
    effect.setOpacity(1.0)

    # Animate the overlay opacity from 1.0 to 0.0 over 5 seconds
    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(5000)  # 5 seconds
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)

    def on_finished():
        print("[DEBUG] Fade animation finished; closing overlay and quitting app")
        overlay.close()
        app.quit()

    anim.finished.connect(on_finished)
    overlay._fade_animation = anim

    def _start_fade_animation():
        print("[DEBUG] Starting fade animation…")
        anim.start()

    # Wait 1 second before starting the fade-out, so the image is visible
    QTimer.singleShot(1000, _start_fade_animation)


def populate_high_scores_for_level(landscape_window: QWidget):
    """
    Populate the High Scores table (tableHighScores) in the landscape view
    for the level shown in lineLevel. Shows only scores for that level,
    sorted by highest to lowest score, then by player name.
    """
    # Find the level name from the landscape UI
    line_level = landscape_window.findChild(QLineEdit, "lineLevel")
    if line_level is None:
        print("Warning: lineLevel not found in landscape window")
        return

    # Prefer the raw level code stored as a property; fall back to the text
    level_code = line_level.property("level_code")
    if not level_code:
        level_code = line_level.text().strip()
    if not level_code:
        print("Warning: no level specified in lineLevel")
        return

    # Find the High Scores table
    table = landscape_window.findChild(QTableWidget, "tableHighScores")
    if table is None:
        print("Warning: tableHighScores not found in main_landscape.ui")
        return

    # Load all players and extract scores for this level
    idx, names = load_players_index()
    rows = []
    for name in names:
        rec = idx.get(name) or {}
        if not isinstance(rec, dict):
            continue
        hs_map = rec.get("high_scores", {})
        if not isinstance(hs_map, dict):
            continue
        score = hs_map.get(level_code)
        if isinstance(score, (int, float)) and score > 0:
            rows.append((name, score))

    # Sort by score (descending), then by name (ascending)
    rows.sort(key=lambda item: (-item[1], item[0].lower()))

    # Build rank map with tie handling: same score => same rank with '='
    score_to_count = {}
    for _, score in rows:
        score_to_count[score] = score_to_count.get(score, 0) + 1

    score_to_rank = {}
    current_rank = 1
    last_score = None
    for _, score in rows:
        if score != last_score:
            score_to_rank[score] = current_rank
            last_score = score
        current_rank += 1

    def format_rank(score_value):
        rank_value = score_to_rank.get(score_value, 0)
        if score_to_count.get(score_value, 0) > 1:
            return str(rank_value) + "="
        return str(rank_value)

    # Populate the table
    table.setSortingEnabled(False)
    table.clearContents()

    # Ensure we have three columns: Rank, Player, Score
    table.setColumnCount(3)
    try:
        table.setHorizontalHeaderLabels(["Rank", "Player", "Score"])
    except Exception:
        pass

    # Hide row numbers (vertical header)
    vh = table.verticalHeader()
    if vh is not None:
        vh.setVisible(False)

    table.setRowCount(len(rows))

    for row_idx, (name, score) in enumerate(rows):
        rank_item = QTableWidgetItem(format_rank(score))
        name_item = QTableWidgetItem(name)
        score_item = QTableWidgetItem(str(score))

        # Align rank and score nicely
        rank_item.setTextAlignment(Qt.AlignCenter)
        score_item.setTextAlignment(Qt.AlignCenter)

        table.setItem(row_idx, 0, rank_item)
        table.setItem(row_idx, 1, name_item)
        table.setItem(row_idx, 2, score_item)

    table.setSortingEnabled(True)


def go_back_to_portrait(landscape_window: QWidget):
    """
    Hide the landscape window and re-show the portrait window that launched it.
    If no portrait window is recorded, just close the landscape window.
    """
    portrait = getattr(landscape_window, "_portrait_window", None)
    if isinstance(portrait, QWidget):
        landscape_window.hide()
        portrait.show()
    else:
        landscape_window.close()

def open_main_landscape_from_portrait(main_window: QWidget):
    """
    Load and show the landscape-mode main window from main_landscape.ui.
    The actual game is not yet connected; this simply displays the UI.
    """
    loader = QUiLoader()
    ui_file = QFile("ui/main_landscape.ui")
    if not ui_file.open(QFile.ReadOnly):
        print("Error: could not open ui/main_landscape.ui")
        return
    landscape_window = loader.load(ui_file)
    ui_file.close()
    if not isinstance(landscape_window, QWidget):
        print("Error: main_landscape.ui did not load correctly.")
        return
    # Remember the portrait window so we can return to it
    landscape_window._portrait_window = main_window

    # Populate Player and Level in landscape view
    # Get currently selected row from portrait view
    portrait_table = main_window.findChild(QTableWidget, "listPlayers")
    if portrait_table is not None:
        row = portrait_table.currentRow()
        if row >= 0:
            name_item = portrait_table.item(row, 0)
            level_item = portrait_table.item(row, 2)

            line_player = landscape_window.findChild(QLineEdit, "linePlayer")
            line_level  = landscape_window.findChild(QLineEdit, "lineLevel")

            if line_player is not None and name_item is not None:
                line_player.setText(name_item.text())

            if line_level is not None and level_item is not None:
                # Prefer the raw level code stored as user data; fall back to the cell text
                raw_level = level_item.data(Qt.UserRole)
                if not raw_level:
                    raw_level = level_item.text()
                # Store the raw level code and show the full, friendly label in the line edit
                line_level.setProperty("level_code", raw_level)
                line_level.setText(get_level_label(raw_level))

            # Populate High Scores for this level
            populate_high_scores_for_level(landscape_window)

    # --- Enforce gameArea as a square equal to 95% of window height and embed the game widget ---
    game_area = landscape_window.findChild(QWidget, "gameArea")
    if game_area is not None:
        def resize_game_area():
            # Calculate target side length (square) = 95% of landscape window height
            target_side = int(landscape_window.height() * 0.95)
            if target_side < 0:
                target_side = 0
            game_area.setFixedSize(target_side, target_side)

        # Initial sizing
        resize_game_area()

        # Patch resizeEvent so the square stays correct on window resize
        original_resize_event = landscape_window.resizeEvent
        def new_resize_event(event, orig=original_resize_event):
            orig(event)
            resize_game_area()
        landscape_window.resizeEvent = new_resize_event


    # Create and embed the game widget into gameArea
    layout = game_area.layout()
    if layout is None:
        layout = QVBoxLayout(game_area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def _create_or_replace_game_widget():
        """Create a new GameWidget for the current player/level, replacing any existing one."""
        # Remove existing game widget, if any
        old_game = getattr(landscape_window, "_game_widget", None)
        if isinstance(old_game, QWidget):
            old_game.setParent(None)
            old_game.deleteLater()

        # Read player from the landscape UI
        line_player = landscape_window.findChild(QLineEdit, "linePlayer")
        line_level = landscape_window.findChild(QLineEdit, "lineLevel")
        player_name = line_player.text() if line_player is not None else ""

        # Retrieve the raw level code from the lineLevel property if available
        level_code = None
        if line_level is not None:
            level_code = line_level.property("level_code")

        # Choose difficulty rules based on the raw level code
        level_key = (level_code or "").lower()
        if "ball01" in level_key or level_key == "1":
            rules = Ball01Rules()
        elif "ball02" in level_key or level_key == "2":
            rules = Ball02Rules()
        elif "ball03" in level_key or level_key == "3":
            rules = Ball03Rules()
        elif "ball04" in level_key or level_key == "4":
            rules = Ball04Rules()
        else:
            # Default to easiest rules if level is unknown
            rules = Ball01Rules()

        # Configure round duration from data/levels.yaml when supported
        try:
            duration_sec = get_level_duration(level_code, default_seconds=20)
            if hasattr(rules, "duration"):
                rules.duration = float(duration_sec)
        except Exception:
            pass

        # Create game widget with the chosen rules
        game = GameWidget(parent=game_area, rules=rules)

        # Pass player and (friendly) full level label into the game if available
        if hasattr(game, "set_player_and_level"):
            display_label = get_level_label(level_code)
            game.set_player_and_level(player_name, display_label)

        # When the round finishes, update the player's high score for this level
        def _on_round_finished(player_name_sig: str, level_label_sig: str, score_sig: int, lw=landscape_window):
            # Determine raw level code from the landscape UI property
            line_level_sig = lw.findChild(QLineEdit, "lineLevel")
            raw_code = None
            if line_level_sig is not None:
                raw_code = line_level_sig.property("level_code")

            # Fallback: try to infer from the full label if property is missing
            if not raw_code and level_label_sig:
                for code, rec in _levels_map().items():
                    if isinstance(rec, dict) and rec.get("full_label") == level_label_sig:
                        raw_code = code
                        break

            update_player_high_score(raw_code, player_name_sig, score_sig, lw)
            # Re-enable buttons now that the round has finished
            btn_play_again_end = lw.findChild(QPushButton, "btnPlayAgain")
            if btn_play_again_end is not None:
                btn_play_again_end.setEnabled(True)

            btn_players_list_end = lw.findChild(QPushButton, "btnPlayersList")
            if btn_players_list_end is not None:
                btn_players_list_end.setEnabled(True)

        try:
            game.roundFinished.connect(_on_round_finished)
        except Exception as e:
            print("Warning: failed to connect roundFinished signal:", str(e))

        layout.addWidget(game)
        landscape_window._game_widget = game

        # Disable navigation/replay buttons while a round is in progress
        btn_play_again_local = landscape_window.findChild(QPushButton, "btnPlayAgain")
        if btn_play_again_local is not None:
            btn_play_again_local.setEnabled(False)

        btn_players_list_local = landscape_window.findChild(QPushButton, "btnPlayersList")
        if btn_players_list_local is not None:
            btn_players_list_local.setEnabled(False)

    # Initial game widget creation
    _create_or_replace_game_widget()

    # Wire up Players List button to return to the portrait view
    btn_players_list = landscape_window.findChild(QPushButton, "btnPlayersList")
    if btn_players_list is None:
        print("Warning: btnPlayersList button not found in main_landscape.ui")
    else:
        btn_players_list.clicked.connect(lambda: go_back_to_portrait(landscape_window))

    # Wire up Play Again button to restart a round at the same level for the same player
    btn_play_again = landscape_window.findChild(QPushButton, "btnPlayAgain")
    if btn_play_again is None:
        print("Warning: btnPlayAgain button not found in main_landscape.ui")
    else:
        def _on_play_again():
            print("[DEBUG] Play Again clicked - restarting round for same player/level")
            _create_or_replace_game_widget()

        btn_play_again.clicked.connect(_on_play_again)

    # Keep a reference so it is not garbage collected
    main_window._landscape_window = landscape_window

    # Hide the portrait window and show the landscape window
    main_window.hide()
    landscape_window.show()

def open_main_portrait_from_splash(splash, clear_current=False):
    if clear_current:
        # Clear any persisted current player so no one is pre-selected
        set_current_player_flag("__NONE__")
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
    # Wire up live, case-insensitive filtering of players by name
    search_edit = main_window.findChild(QLineEdit, "editSearch")
    if search_edit is None:
        search_edit = main_window.findChild(QLineEdit, "lineSearch")
    if search_edit is not None:
        # Show a built-in clear (X) icon to erase the search text
        try:
            search_edit.setClearButtonEnabled(True)
        except Exception:
            pass

        def _on_search(text: str):
            # Filter only by player name, ignoring case
            populate_players_list(main_window, text)
        search_edit.textChanged.connect(_on_search)
    else:
        print("Warning: search QLineEdit (editSearch/lineSearch) not found in main_portrait.ui")
    # Wire up Exit button in gameOutcome group box with fade-out animation
    btn_exit = main_window.findChild(QPushButton, "btnExit")
    if btn_exit is not None:
        btn_exit.clicked.connect(lambda: exit_with_fade(main_window))
    # Wire up Play button to open the landscape UI (main_landscape.ui)
    btn_play = main_window.findChild(QPushButton, "btnPlay")
    if btn_play is None:
        print("Warning: btnPlay button not found in main_portrait.ui")
    else:
        # Only allow Play if a player is selected; otherwise show a toast
        def _on_play():
            table = main_window.findChild(QTableWidget, "listPlayers")
            if table is None or table.currentRow() < 0:
                show_toast(main_window, "Select a player")
                return
            open_main_landscape_from_portrait(main_window)

        btn_play.clicked.connect(_on_play)
        btn_play.setEnabled(False)
    # Keep a reference so it is not garbage collected
    splash._main_window = main_window
    main_window.show()
    splash.close()


def open_main_landscape_from_splash(splash: QWidget):
    """
    From the splash screen, go straight to the landscape game view.
    This reuses the portrait->landscape pipeline so that:
      - the current player (if any) is respected
      - the gameArea, Go Back, and GameWidget are fully wired
    """
    # First, open the portrait window WITHOUT clearing the current player
    open_main_portrait_from_splash(splash, clear_current=False)

    # Retrieve the portrait window created by open_main_portrait_from_splash
    main_window = getattr(splash, "_main_window", None)
    if isinstance(main_window, QWidget):
        # Immediately transition to the landscape view for that portrait window
        open_main_landscape_from_portrait(main_window)

def make_splash_screen(loader: QUiLoader) -> QWidget:
    splash_file = QFile("ui/splash_portrait.ui")
    if not splash_file.open(QFile.ReadOnly):
        print("Error: could not open ui/splash_portrait.ui")
        sys.exit(1)
    splash = loader.load(splash_file)
    splash_file.close()


    # Personalise labelGlasses2 with current player's name if present
    label2 = splash.findChild(QLabel, "labelGlasses2")
    if label2 is not None:
        # Attempt to read current player name
        try:
            path = os.path.join(os.getcwd(), "data", "players.yaml")
            current_name = None
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    pdata = yaml.safe_load(f)
                if isinstance(pdata, dict):
                    for nm, rec in pdata.items():
                        if isinstance(rec, dict) and rec.get("is_current_player") is True:
                            current_name = nm
                            break
            # Replace placeholder {name} in label text
            if current_name:
                base = label2.text()
                label2.setText(base.replace("{name}", current_name))
        except Exception:
            pass

    if not isinstance(splash, QWidget):
        print("Error: splash_portrait.ui did not load correctly.")
        sys.exit(1)

    btn = splash.findChild(QPushButton, "btnLetsPlay")
    if btn is None:
        print("Warning: btnLetsPlay button not found in splash_portrait.ui")
    else:
        btn.clicked.connect(lambda: open_main_landscape_from_splash(splash))

    btn_not_me = splash.findChild(QPushButton, "btnNotMe")
    if btn_not_me is None:
        print("Warning: btnNotMe button not found in splash_portrait.ui")
    else:
        btn_not_me.clicked.connect(lambda: open_main_portrait_from_splash(splash, True))

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
