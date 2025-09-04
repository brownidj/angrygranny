import tkinter as tk
from tkinter import messagebox, simpledialog

class PlayerPanel(tk.Frame):
    """
    A frame that encapsulates:
      - the player listbox
      - Add Player dialogue
      - Delete Player dialogue
      - selection tracking
    """
    def __init__(self, parent, player_manager):
        super().__init__(parent)
        self.pm = player_manager
        self.selected = None

        # Listbox
        self.listbox = tk.Listbox(self, height=10, width=30)
        self.listbox.pack(side=tk.LEFT, fill=tk.Y, padx=(0,5))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Button(btn_frame, text="Add", command=self._add).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="Delete", command=self._delete).pack(fill=tk.X, pady=2)

        self.reload()

    def reload(self):
        """Refresh list from PlayerManager."""
        self.listbox.delete(0, tk.END)
        for nickname in self.pm.get_nicknames():
            self.listbox.insert(tk.END, nickname)
        self.listbox.update()

    def _on_select(self, _):
        sel = self.listbox.curselection()
        self.selected = self.listbox.get(sel[0]) if sel else None

    def _add(self):
        popup = tk.Toplevel(self)
        # ... same as before, but calling self.pm.add_player(...)
        # after success:
        popup.destroy()
        self.reload()

    def _delete(self):
        if not self.selected:
            messagebox.showwarning("No selection", "Select a player first.")
            return
        pw = simpledialog.askstring("Confirm Delete", f"Password for {self.selected}:", show="*")
        try:
            self.pm.delete_player(self.selected, pw)
        except Exception as e:
            messagebox.showerror("Error", str(e))
        else:
            self.reload()
            self.selected = None