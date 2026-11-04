"""Timer logic for the smudge timer and the hunt cooldown timer.

This file has no UI code and no hotkey code on purpose. Keeping the
logic separate means it can be unit tested without opening a window
(see tests/test_logic.py).

All times are floats from time.perf_counter(). perf_counter is used
instead of time.time() because it never jumps when Windows syncs the
system clock, so a running timer can't suddenly skip.
"""

IDLE = "idle"
RUNNING = "running"
STOPPED = "stopped"


class Stopwatch:
    """A count-up timer with three states.

    idle    -> shows 0, waiting to be started
    running -> counting up
    stopped -> frozen on the time it was stopped at

    toggle() follows the controls you asked for:
      1st press starts, 2nd press stops, a press while stopped starts
      again from 0. Holding the key calls clear() instead.
    """

    def __init__(self):
        self.state = IDLE
        self.start_time = 0.0
        self.frozen_elapsed = 0.0

    def toggle(self, t):
        if self.state == RUNNING:
            self.frozen_elapsed = t - self.start_time
            self.state = STOPPED
        else:
            # Idle or stopped: start a fresh count from this moment.
            self.start_time = t
            self.frozen_elapsed = 0.0
            self.state = RUNNING

    def clear(self):
        self.state = IDLE
        self.start_time = 0.0
        self.frozen_elapsed = 0.0

    def elapsed(self, now):
        if self.state == RUNNING:
            return now - self.start_time
        if self.state == STOPPED:
            return self.frozen_elapsed
        return 0.0


# Each marker is (seconds, short label shown once that time has passed).
# Values are from the Phasmophobia wiki / community guides:
#   - A smudge stops hunts for 90 s, but a Demon only for 60 s and a
#     Spirit for 180 s. So if a ghost hunts between 60 and 90 s after a
#     smudge it's a Demon; if it hunts between 90 and 180 s it is not a
#     Spirit.
SMUDGE_MARKERS = [
    (60.0, "Demon can hunt"),
    (90.0, "Most can hunt (not Spirit before 180)"),
    (180.0, "Spirit can hunt"),
]

# After a hunt ends, the next hunt can't start for 25 s (Demon: 20 s).
HUNT_MARKERS = [
    (20.0, "Demon can hunt"),
    (25.0, "Any ghost can hunt"),
]

SMUDGE_BAR_MAX = 180.0
HUNT_BAR_MAX = 25.0


def current_hint(markers, elapsed, before_first):
    """Return the label of the last marker that has been passed.

    before_first is the text shown before the first marker is reached.
    """
    hint = before_first
    for i in range(len(markers)):
        seconds, label = markers[i]
        if elapsed >= seconds:
            hint = label
    return hint


def format_time(seconds):
    """Format seconds as M:SS.t (e.g. 1:05.3)."""
    if seconds < 0:
        seconds = 0.0
    tenths = int(seconds * 10)
    minutes = tenths // 600
    secs = (tenths // 10) % 60
    tenth = tenths % 10
    return f"{minutes}:{secs:02d}.{tenth}"
