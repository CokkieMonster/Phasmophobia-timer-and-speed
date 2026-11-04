"""Ghost speed from tapping along to its footsteps.

How the conversion works
------------------------
You tap once per footstep, which gives a tap rate (BPM = taps per
minute). The formula that turns that into metres per second is the one
the Zero-Network "Unofficial Phasmophobia Cheat Sheet" uses:

    speed = BPM / (modifier * (60 + 0.075 * BPM))

modifier is your lobby's ghost speed setting (0.5 for 50 %, 1.0 for
100 %, 1.5 for 150 %). Dividing by it gives the ghost's *base* speed, so
1.7 m/s always means "normal ghost" no matter what difficulty you play.

Sanity check: 115 BPM -> 115 / (60 + 8.6) = 1.68 m/s, which matches the
community's "a normal 1.7 m/s ghost steps at about 115 BPM".
"""

# Speed setting options shown in the settings window.
SPEED_MODIFIERS = [0.5, 0.75, 1.0, 1.25, 1.5]


def bpm_to_speed(bpm, modifier=1.0):
    if bpm <= 0:
        return 0.0
    return bpm / (modifier * (60.0 + 0.075 * bpm))


class TapSpeedMeter:
    """Keeps the most recent taps and turns them into a speed.

    max_taps:   how many recent taps to average over. More taps = steadier
                number but slower to react when the ghost speeds up.
    idle_reset: a gap longer than this (seconds) starts a new measurement.
                The slowest footsteps (a Deogen right next to you, about
                0.4 m/s) are roughly 2.4 s apart, so 3 s still counts them.
    """

    def __init__(self, max_taps=12, idle_reset=3.0):
        self.max_taps = max_taps
        self.idle_reset = idle_reset
        self.taps = []

    def tap(self, t):
        if len(self.taps) > 0 and t - self.taps[-1] > self.idle_reset:
            self.taps = []
        self.taps.append(t)
        if len(self.taps) > self.max_taps:
            self.taps.pop(0)

    def clear(self):
        self.taps = []

    def tap_count(self):
        return len(self.taps)

    def bpm(self):
        """Average taps per minute over the stored taps.

        We use (number of gaps) / (total time span) rather than averaging
        each gap's own BPM. Averaging per-gap BPMs is biased: one tap that
        lands a little early makes a very large BPM for that gap and drags
        the average up. Total span treats every tap fairly.

        At least 3 taps (2 gaps) are needed before showing a number,
        because a single gap is mostly noise from your reaction time.
        """
        if len(self.taps) < 3:
            return 0.0
        span = self.taps[-1] - self.taps[0]
        if span <= 0:
            return 0.0
        gaps = len(self.taps) - 1
        return 60.0 * gaps / span

    def taps_per_second(self):
        return self.bpm() / 60.0

    def speed(self, modifier=1.0):
        return bpm_to_speed(self.bpm(), modifier)
