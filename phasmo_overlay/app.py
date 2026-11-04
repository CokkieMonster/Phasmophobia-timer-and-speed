"""Ties everything together: hotkey events in, timer/speed updates, redraws."""

import queue
import sys
import time
import tkinter as tk

from . import config
from .hotkeys import HotkeyListener, binding_id
from .overlay import Overlay
from .settings_window import SettingsWindow
from .speed import TapSpeedMeter
from .timers import Stopwatch

TIMER_ACTIONS = ("smudge", "hunt")


class App:
    def __init__(self):
        _make_dpi_aware()
        self.cfg = config.load()
        self.root = tk.Tk()
        self.root.title("Phasmo Timer")

        self.timers = {"smudge": Stopwatch(), "hunt": Stopwatch()}
        self.meter = TapSpeedMeter(max_taps=self.cfg["max_taps"])

        # For hold-to-clear: when each timer key went down, and which
        # holds have already cleared their timer.
        self.down_times = {}
        self.hold_fired = set()

        self.capture_callback = None
        self.settings_window = None

        self.overlay = Overlay(self.root, self.cfg, self.on_moved, self.open_settings)
        self.hotkeys = HotkeyListener()
        self.hotkeys.set_bindings(self.cfg["bindings"])
        self.hotkeys.start()

    def run(self):
        self.poll()
        self.root.mainloop()
        self.hotkeys.stop()

    def quit(self):
        config.save(self.cfg)
        self.root.destroy()

    # ---------- main loop ----------

    def poll(self):
        """Runs every ~16 ms on the UI thread."""
        while True:
            try:
                kind, data, t = self.hotkeys.events.get_nowait()
            except queue.Empty:
                break
            self.handle_event(kind, data, t)

        now = time.perf_counter()
        hold = self.cfg["hold_to_clear"]
        hold_progress = {}
        for action in TIMER_ACTIONS:
            if action in self.down_times and action not in self.hold_fired:
                held_for = now - self.down_times[action]
                if held_for >= hold:
                    self.timers[action].clear()
                    self.hold_fired.add(action)
                else:
                    hold_progress[action] = held_for / hold

        lock_name = self.cfg["bindings"]["lock"]["name"]
        self.overlay.draw(now, self.timers["smudge"], self.timers["hunt"], self.meter,
                          hold_progress, lock_name)
        self.root.after(16, self.poll)

    def handle_event(self, kind, action, t):
        if kind == "capture":
            callback = self.capture_callback
            self.capture_callback = None
            if callback is not None:
                callback(action)  # here "action" is the captured binding (or None)
            return

        if kind == "down":
            if action in TIMER_ACTIONS:
                # Don't act yet: we only know if it's a tap or a hold
                # once the key comes back up (or the hold time passes).
                self.down_times[action] = t
                self.hold_fired.discard(action)
            elif action == "tap":
                self.meter.tap(t)
            elif action == "lock":
                self.overlay.toggle_locked()
            elif action == "hide":
                self.overlay.toggle_visible()
            elif action == "settings":
                self.open_settings()

        elif kind == "up":
            if action in TIMER_ACTIONS and action in self.down_times:
                pressed_at = self.down_times.pop(action)
                if action in self.hold_fired:
                    self.hold_fired.discard(action)  # it was a hold: already cleared
                else:
                    # A short press. Use the time the key went *down*, so the
                    # timer starts/stops at the moment you reacted, not
                    # when you let go.
                    self.timers[action].toggle(pressed_at)

    # ---------- called by the overlay / settings window ----------

    def on_moved(self, x, y):
        self.cfg["x"] = x
        self.cfg["y"] = y
        config.save(self.cfg)

    def open_settings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self)
        else:
            self.settings_window.win.lift()
            self.settings_window.win.focus_force()

    def capture_binding(self, callback):
        self.capture_callback = callback
        self.hotkeys.begin_capture()

    def set_binding(self, action, binding):
        """Bind action to binding. If another action already uses that key,
        the two swap keys, so no action is ever left without a key."""
        bindings = self.cfg["bindings"]
        old = bindings[action]
        for other in bindings:
            if other != action and binding_id(bindings[other]) == binding_id(binding):
                bindings[other] = old
        bindings[action] = binding
        self.hotkeys.set_bindings(bindings)
        config.save(self.cfg)

    def settings_changed(self):
        self.meter.max_taps = self.cfg["max_taps"]
        self.overlay.apply_look()
        config.save(self.cfg)


def _make_dpi_aware():
    """Without this, Windows blurs the overlay on screens set to 125%+
    scaling, because it stretches a low-res copy of the window."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
