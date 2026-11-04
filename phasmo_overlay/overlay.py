"""The on-screen overlay drawn above the game.

Everything is drawn on one tkinter Canvas and redrawn ~60 times a second.
Clearing and redrawing a few shapes is cheap, and it is far simpler than
keeping track of which label changed.

How it stays on top of the game
-------------------------------
* overrideredirect(True) removes the title bar and border.
* "-topmost" keeps it above other windows. This only works when the game
  runs in *Windowed Borderless*: true fullscreen bypasses the desktop
  compositor, so nothing can be drawn above it.
* Click-through: Windows lets clicks pass through a window that has the
  WS_EX_TRANSPARENT + WS_EX_LAYERED extended styles. tkinter has no
  setting for that, so we call the Win32 API directly through ctypes
  (part of the standard library, so no extra install).
"""

import ctypes
import sys
import tkinter as tk

from .timers import (HUNT_BAR_MAX, HUNT_MARKERS, IDLE, RUNNING, SMUDGE_BAR_MAX,
                     SMUDGE_MARKERS, STOPPED, current_hint, format_time)

IS_WINDOWS = sys.platform == "win32"

# Win32 constants (from WinUser.h)
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020   # mouse clicks fall through to the window below
WS_EX_TOOLWINDOW = 0x00000080    # no taskbar button, not in Alt+Tab
WS_EX_NOACTIVATE = 0x08000000    # clicking it never steals focus from the game

# Colours
BG = "#0f1216"
BORDER_UNLOCKED = "#f59e0b"
TEXT = "#f3f4f6"
DIM = "#6b7280"
AMBER = "#fbbf24"
GREEN = "#34d399"
ORANGE = "#fb923c"
RED = "#f87171"
BLUE = "#60a5fa"
TRACK = "#252a31"

MONO = "Consolas"   # fixed-width digits, so the time doesn't wiggle as it changes
SANS = "Segoe UI"


class Overlay:
    def __init__(self, root, cfg, on_moved, on_right_click):
        self.root = root
        self.cfg = cfg
        self.on_moved = on_moved
        self.locked = True
        self.drag_start = None

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=BG)

        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        # Dragging (only does anything while unlocked, because when locked
        # the clicks pass through to the game and never reach us).
        self.canvas.bind("<ButtonPress-1>", self._drag_begin)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_end)
        self.canvas.bind("<ButtonPress-3>", lambda e: on_right_click())

        self.apply_look()
        self.root.update_idletasks()
        self.set_locked(True)
        self._keep_on_top()

    # ---------- window handling ----------

    def size(self):
        s = self.cfg["scale"]
        return int(300 * s), int(204 * s)

    def apply_look(self):
        w, h = self.size()
        self.root.geometry(f"{w}x{h}+{int(self.cfg['x'])}+{int(self.cfg['y'])}")
        self.root.attributes("-alpha", self.cfg["opacity"])

    def _hwnd(self):
        # winfo_id() is Tk's inner window; the real top-level window that
        # Windows moves and styles is its parent.
        return ctypes.windll.user32.GetParent(self.root.winfo_id())

    def _set_click_through(self, enabled):
        if not IS_WINDOWS:
            return
        user32 = ctypes.windll.user32
        hwnd = self._hwnd()
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        if enabled:
            style = style | WS_EX_TRANSPARENT
        else:
            style = style & ~WS_EX_TRANSPARENT
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def set_locked(self, locked):
        self.locked = locked
        self._set_click_through(locked)

    def toggle_locked(self):
        self.set_locked(not self.locked)
        if self.locked:
            self.on_moved(self.root.winfo_x(), self.root.winfo_y())

    def toggle_visible(self):
        if self.root.state() == "withdrawn":
            self.root.deiconify()
            self.root.update_idletasks()
            self._set_click_through(self.locked)  # re-apply in case Windows reset it
        else:
            self.root.withdraw()

    def _keep_on_top(self):
        # Some games push themselves to the front when they regain focus.
        # Re-asserting "topmost" every 2 s puts the overlay back above them.
        if self.root.state() != "withdrawn":
            self.root.attributes("-topmost", True)
            self.root.lift()
        self.root.after(2000, self._keep_on_top)

    def _drag_begin(self, e):
        if not self.locked:
            self.drag_start = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _drag_move(self, e):
        if self.drag_start is not None:
            x = e.x_root - self.drag_start[0]
            y = e.y_root - self.drag_start[1]
            self.root.geometry(f"+{x}+{y}")

    def _drag_end(self, e):
        if self.drag_start is not None:
            self.drag_start = None
            self.on_moved(self.root.winfo_x(), self.root.winfo_y())

    # ---------- drawing ----------

    def draw(self, now, smudge, hunt, meter, hold_progress, lock_key_name):
        """Redraw everything.

        smudge, hunt:   Stopwatch objects
        meter:          TapSpeedMeter
        hold_progress:  dict action -> 0..1 while a timer key is being held
        """
        c = self.canvas
        c.delete("all")
        s = self.cfg["scale"]
        w, h = self.size()
        pad = 12 * s

        if not self.locked:
            c.create_rectangle(1, 1, w - 2, h - 2, outline=BORDER_UNLOCKED, width=2)

        y = pad
        y = self._draw_timer_row(y, "SMUDGE", smudge, now, SMUDGE_MARKERS, SMUDGE_BAR_MAX,
                                 "Smudged: no hunts", self._smudge_color,
                                 hold_progress.get("smudge", 0.0))
        y = y + 8 * s
        y = self._draw_timer_row(y, "HUNT CD", hunt, now, HUNT_MARKERS, HUNT_BAR_MAX,
                                 "Too soon to hunt again", self._hunt_color,
                                 hold_progress.get("hunt", 0.0))
        y = y + 8 * s
        self._draw_speed_row(y, meter)

        if not self.locked:
            c.create_text(w / 2, h - 12 * s, text=f"UNLOCKED: drag to move, {lock_key_name} to lock",
                          fill=BORDER_UNLOCKED, font=(SANS, int(7 * s)))

    def _smudge_color(self, t):
        if t < 60:
            return GREEN
        if t < 90:
            return AMBER
        if t < 180:
            return ORANGE
        return RED

    def _hunt_color(self, t):
        if t < 20:
            return GREEN
        if t < 25:
            return AMBER
        return RED

    def _draw_timer_row(self, y, title, sw, now, markers, bar_max, before_first, color_fn, hold):
        c = self.canvas
        s = self.cfg["scale"]
        w = self.size()[0]
        pad = 12 * s
        t = sw.elapsed(now)

        if sw.state == RUNNING:
            time_color = TEXT
        elif sw.state == STOPPED:
            time_color = AMBER
        else:
            time_color = DIM

        c.create_text(pad, y, text=title, anchor="nw", fill=DIM, font=(SANS, int(8 * s), "bold"))
        state_text = {IDLE: "", RUNNING: "", STOPPED: "STOPPED"}[sw.state]
        if state_text:
            c.create_text(pad, y + 14 * s, text=state_text, anchor="nw", fill=AMBER,
                          font=(SANS, int(7 * s), "bold"))
        c.create_text(w - pad, y - 3 * s, text=format_time(t), anchor="ne", fill=time_color,
                      font=(MONO, int(17 * s), "bold"))

        # Progress bar with tick marks at each marker.
        bar_y = y + 30 * s
        bar_h = 5 * s
        left = pad
        right = w - pad
        c.create_rectangle(left, bar_y, right, bar_y + bar_h, fill=TRACK, width=0)
        if sw.state != IDLE:
            frac = min(t / bar_max, 1.0)
            c.create_rectangle(left, bar_y, left + (right - left) * frac, bar_y + bar_h,
                               fill=color_fn(t), width=0)
        for i in range(len(markers)):
            mx = left + (right - left) * min(markers[i][0] / bar_max, 1.0)
            c.create_line(mx, bar_y - 2 * s, mx, bar_y + bar_h + 2 * s, fill=TEXT, width=1)

        # Hint line, or "hold to clear" feedback while the key is held.
        hint_y = bar_y + bar_h + 4 * s
        if hold > 0.25:
            c.create_rectangle(left, hint_y + 2 * s, left + (right - left) * hold, hint_y + 4 * s,
                               fill=RED, width=0)
            c.create_text(left, hint_y + 6 * s, text="hold to clear...", anchor="nw", fill=RED,
                          font=(SANS, int(8 * s)))
        elif sw.state != IDLE:
            hint = current_hint(markers, t, before_first)
            c.create_text(left, hint_y, text=hint, anchor="nw", fill=color_fn(t),
                          font=(SANS, int(8 * s)))
        return hint_y + 16 * s

    def _draw_speed_row(self, y, meter):
        c = self.canvas
        s = self.cfg["scale"]
        w = self.size()[0]
        pad = 12 * s
        mod = self.cfg["speed_modifier"]

        c.create_text(pad, y, text="SPEED", anchor="nw", fill=DIM, font=(SANS, int(8 * s), "bold"))
        n = meter.tap_count()
        if meter.bpm() <= 0:
            if n == 0:
                msg = "tap along to footsteps"
            else:
                msg = f"keep tapping ({n}/3)"
            c.create_text(w - pad, y + 2 * s, text=msg, anchor="ne", fill=DIM, font=(SANS, int(9 * s)))
            return

        ms = meter.speed(mod)
        if ms < 1.55:
            col = BLUE    # slower than a normal ghost
        elif ms > 1.85:
            col = RED     # faster than a normal ghost
        else:
            col = TEXT
        c.create_text(w - pad, y - 3 * s, text=f"{ms:.2f} m/s", anchor="ne", fill=col,
                      font=(MONO, int(17 * s), "bold"))
        info = f"{meter.taps_per_second():.2f} taps/s  ·  {n} taps  ·  lobby {int(mod * 100)}%"
        c.create_text(pad, y + 24 * s, text=info, anchor="nw", fill=DIM, font=(SANS, int(8 * s)))
