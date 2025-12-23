# ChatGPT Patch Log
A running record of code changes applied via ChatGPT, including the explicit edits and the reasoning. Keep this under version control.

> Timezone: Australia/Brisbane (AEST)

---

## 2025-09-18 09:00 — Ensure app terminates when player clicks **No** on “Play again?”
**Files updated:** `game_launcher.py`

### What changed (high level)
- Added thread-safe UI helper `_ask_yes_no_on_main` to show `messagebox.askyesno` on the Tk main thread.
- Added `_shutdown_app` to cleanly quit and destroy all Tk windows.
- Modified replay prompt logic so that when the user selects **No**, the app closes all windows and ends the game.
- (Follow-up fix) Moved helper methods to class scope so `self._ask_yes_no_on_main` exists, resolving `AttributeError`.

### Why
- Tkinter is not thread-safe. Prompting from a worker thread can crash or hang; the helper schedules the dialog on the main loop.
- Users expect **No** to end the game; previously it only broke the loop but could leave windows open.
- The `AttributeError` occurred because the helper methods were nested inside `run`. Moving them to class scope makes them accessible from the game thread.

### Exact edits (patch-style summary)
- In `game_launcher.py`:
  1. **Replay prompt**
     - Before:
       ```python
       msg += "\n\nPlay again?"
       again = messagebox.askyesno("Game Over", msg)
       if not again:
           break
       ```
     - After:
       ```python
       msg += "\n\nPlay again?"
       again = self._ask_yes_no_on_main("Game Over", msg)
       if not again:
           self._shutdown_app()
           break
       ```
  2. **Add (class-level) helpers**
     ```python
     def _ask_yes_no_on_main(self, title: str, message: str) -> bool:
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
         def _do_shutdown():
             try:
                 for w in list(self.root.winfo_children()):
                     try:
                         w.destroy()
                     except Exception:
                         pass
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
         self.root.after(0, _do_shutdown)
     ```

---

## 2025-09-18 09:05 — Add 3‑option replay dialog with level‑up support
**Files updated:** `game_launcher.py`

### What changed (high level)
- Read per‑level thresholds from `constants.txt` entries like `max_level_ball01 = 5`.
- After each round, if `score >= threshold` and a next level exists (up to `ball04`), show a custom modal dialog with **Exit**, **Continue**, **Level up**.
- **Exit** quits the app; **Continue** replays the same level; **Level up** launches the next level immediately.
- Preserved the 2‑button flow (**Continue** / **Exit**) when the threshold isn’t reached or at the top level.
- All dialogs are created on the Tk main thread using an `Event` to block the worker safely.

### Why
- The yes/no dialog no longer fit the design once a third option (**Level up**) became necessary based on a configurable per‑level score threshold.

### Exact edits (patch‑style summary)
- In `game_launcher.py`:
  1. **Parsing thresholds**
     - Added `import re` and a helper `_load_level_thresholds()` to parse `constants.txt` lines matching `max_level_(ball0[1-4]) = (\d+)`.
     - Stored thresholds in `self.level_thresholds`.
  2. **Track current level**
     - Introduced `current_level` local in `_game_thread` and replaced uses of `level` within the loop.
  3. **Next level helper**
     - Added `_get_next_level()` to map `ball01→ball02→ball03→ball04`, returning `None` at the top.
  4. **3‑option dialog**
     - Added `_ask_replay_choice_on_main()` to show modal **Exit / Continue / Level up** dialog when eligible; otherwise fall back to `_ask_yes_no_on_main()` for **Continue / Exit**.
  5. **Flow integration**
     - After computing `score`, checked eligibility and routed to the appropriate dialog; applied action (exit / continue / level up) accordingly.

---

## 2025-09-18 09:10 — Fix uninitialized `score` causing crash in replay dialog
**Files updated:** `game_launcher.py`

### What changed
- Initialize `score = 0` immediately after the game subprocess finishes and before checking for `last_score.json` so level‑up logic always has a defined value.

### Why
- When no `last_score.json` was present, `score` was referenced before assignment, raising `UnboundLocalError`.

### Exact edit
- Inserted:
  ```python
  # Default score in case no result file is written
  score = 0
  ```
  directly before:
  ```python
  result_file = "last_score.json"
  if os.path.exists(result_file):
      ...
  ```
