

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

## How to use this log going forward
- Each time ChatGPT edits your code, an entry will be appended here with:
  - **Files updated**
  - **What changed**
  - **Why** (reasoning)
  - **Exact edits** (succinct patch-style summary)
- You can rename this file to `CHANGELOG.md` if you prefer Markdown semantics; the content is already Markdown-friendly.
