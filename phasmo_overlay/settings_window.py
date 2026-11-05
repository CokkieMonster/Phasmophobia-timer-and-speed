"""Settings window: rebind keys and change options.

Every change is applied and saved straight away, so there's no Save
button to forget.
"""

import tkinter as tk
from tkinter import ttk

from . import config
from .speed import SPEED_MODIFIERS


class SettingsWindow:
    def __init__(self, app):
        self.app = app
        self.cfg = app.cfg
        self.win = tk.Toplevel(app.root)
        self.win.title("Phasmo Timer - Settings")
        self.win.attributes("-topmost", True)  # otherwise it can open behind the game
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.bind_buttons = {}

        frame = ttk.Frame(self.win, padding=14)
        frame.pack(fill="both", expand=True)
        row = 0

        # --- keybinds ---
        ttk.Label(frame, text="Keybinds", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w")
        row = row + 1
        ttk.Label(frame, text="Click a button, then press a key or mouse button\n"
                              "(Left click, Mouse3/4/5). Esc cancels.",
                  foreground="#666").grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 6))
        row = row + 1
        for i in range(len(config.ACTIONS)):
            action, label = config.ACTIONS[i]
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=2)
            btn = ttk.Button(frame, width=16, command=lambda a=action: self.start_rebind(a))
            btn.grid(row=row, column=1, sticky="e", pady=2)
            self.bind_buttons[action] = btn
            row = row + 1
        self.refresh_bind_labels()

        ttk.Separator(frame).grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row = row + 1

        # --- options ---
        ttk.Label(frame, text="Options", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w")
        row = row + 1

        ttk.Label(frame, text="Lobby ghost speed").grid(row=row, column=0, sticky="w", pady=2)
        labels = []
        for i in range(len(SPEED_MODIFIERS)):
            labels.append(str(int(SPEED_MODIFIERS[i] * 100)) + "%")
        self.speed_var = tk.StringVar(value=str(int(self.cfg["speed_modifier"] * 100)) + "%")
        speed_box = ttk.Combobox(frame, values=labels, textvariable=self.speed_var,
                                 state="readonly", width=8)
        speed_box.grid(row=row, column=1, sticky="e")
        speed_box.bind("<<ComboboxSelected>>", self.on_speed)
        row = row + 1

        self.hold_var = tk.DoubleVar(value=self.cfg["hold_to_clear"])
        row = self.add_spin(frame, row, "Hold to clear (seconds)", self.hold_var, 0.3, 2.0, 0.1, "hold_to_clear", float)

        self.taps_var = tk.IntVar(value=self.cfg["max_taps"])
        row = self.add_spin(frame, row, "Taps averaged for speed", self.taps_var, 4, 30, 1, "max_taps", int)

        self.opacity_var = tk.DoubleVar(value=self.cfg["opacity"])
        row = self.add_slider(frame, row, "Opacity", self.opacity_var, 0.3, 1.0, "opacity")

        self.scale_var = tk.DoubleVar(value=self.cfg["scale"])
        row = self.add_slider(frame, row, "Size", self.scale_var, 0.7, 2.0, "scale")

        ttk.Separator(frame).grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row = row + 1

        buttons = ttk.Frame(frame)
        buttons.grid(row=row, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Reset position", command=self.reset_position).pack(side="left")
        ttk.Button(buttons, text="Quit app", command=app.quit).pack(side="left", padx=6)
        ttk.Button(buttons, text="Close", command=self.close).pack(side="right")

        self.win.focus_force()

    # --- helpers to build rows ---

    def add_spin(self, frame, row, label, var, low, high, step, key, cast):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=2)
        spin = ttk.Spinbox(frame, from_=low, to=high, increment=step, textvariable=var, width=8,
                           command=lambda: self.set_value(key, var, cast))
        spin.grid(row=row, column=1, sticky="e")
        spin.bind("<FocusOut>", lambda e: self.set_value(key, var, cast))
        spin.bind("<Return>", lambda e: self.set_value(key, var, cast))
        return row + 1

    def add_slider(self, frame, row, label, var, low, high, key):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=2)
        slider = ttk.Scale(frame, from_=low, to=high, variable=var, length=140,
                           command=lambda v: self.set_value(key, var, float))
        slider.grid(row=row, column=1, sticky="e")
        return row + 1

    def set_value(self, key, var, cast):
        try:
            value = cast(var.get())
        except (ValueError, tk.TclError):
            return  # half-typed number; ignore until it's valid
        self.cfg[key] = value
        self.app.settings_changed()

    # --- keybinds ---

    def refresh_bind_labels(self):
        for action in self.bind_buttons:
            self.bind_buttons[action].configure(text=self.cfg["bindings"][action]["name"])

    def start_rebind(self, action):
        self.bind_buttons[action].configure(text="Press a key...")
        self.app.capture_binding(lambda b: self.finish_rebind(action, b))

    def finish_rebind(self, action, binding):
        if binding is not None:
            self.app.set_binding(action, binding)
        self.refresh_bind_labels()

    # --- other ---

    def on_speed(self, event=None):
        text = self.speed_var.get().rstrip("%")
        self.cfg["speed_modifier"] = int(text) / 100.0
        self.app.settings_changed()

    def reset_position(self):
        self.cfg["x"] = config.DEFAULTS["x"]
        self.cfg["y"] = config.DEFAULTS["y"]
        self.app.settings_changed()

    def close(self):
        self.app.settings_window = None
        self.win.destroy()
