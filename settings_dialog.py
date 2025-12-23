import tkinter as tk

class SettingsDialog:
    """
    A dialog for adjusting game settings, currently only toggles sound on/off.
    """
    def __init__(self, parent, sound_on: bool):
        self.parent   = parent
        self.sound_on = sound_on

    def show(self) -> bool:
        dlg = tk.Toplevel(self.parent)
        dlg.title("Settings")
        dlg.geometry("300x150")

        # Sound on/off checkbox
        sound_var = tk.BooleanVar(value=self.sound_on)
        tk.Checkbutton(dlg, text="Sound On", variable=sound_var).pack(padx=10, pady=10)

        # Apply and close
        def apply_and_close():
            self.sound_on = sound_var.get()
            dlg.destroy()

        tk.Button(dlg, text="OK", command=apply_and_close).pack(pady=(0, 10))
        dlg.wait_window()
        return self.sound_on