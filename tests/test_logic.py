"""Unit tests for the timer and speed logic. Run with:  python -m pytest"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phasmo_overlay.config import DEFAULTS
from phasmo_overlay.speed import TapSpeedMeter, bpm_to_speed
from phasmo_overlay.timers import (HUNT_MARKERS, IDLE, RUNNING, SMUDGE_MARKERS,
                                   STOPPED, Stopwatch, current_hint, format_time)


def test_stopwatch_start_stop_restart():
    sw = Stopwatch()
    assert sw.state == IDLE
    sw.toggle(10.0)
    assert sw.state == RUNNING
    assert sw.elapsed(15.0) == 5.0
    sw.toggle(20.0)
    assert sw.state == STOPPED
    assert sw.elapsed(100.0) == 10.0  # frozen
    sw.toggle(50.0)  # press while stopped -> fresh start
    assert sw.state == RUNNING
    assert sw.elapsed(51.0) == 1.0


def test_stopwatch_clear():
    sw = Stopwatch()
    sw.toggle(0.0)
    sw.clear()
    assert sw.state == IDLE
    assert sw.elapsed(99.0) == 0.0


def test_hints():
    assert current_hint(SMUDGE_MARKERS, 10, "safe") == "safe"
    assert current_hint(SMUDGE_MARKERS, 61, "safe") == "Demon can hunt"
    assert current_hint(SMUDGE_MARKERS, 200, "safe") == "Spirit can hunt"
    assert current_hint(HUNT_MARKERS, 22, "x") == "Demon can hunt"


def test_format_time():
    assert format_time(0) == "0:00.0"
    assert format_time(65.37) == "1:05.3"
    assert format_time(-1) == "0:00.0"


def test_normal_ghost_speed():
    # ~115 BPM should be about a normal 1.7 m/s ghost
    assert abs(bpm_to_speed(115) - 1.68) < 0.01
    # same footsteps on 150% lobby -> base speed is lower
    assert bpm_to_speed(115, 1.5) < bpm_to_speed(115, 1.0)


def test_meter_needs_three_taps():
    m = TapSpeedMeter()
    m.tap(0.0)
    m.tap(0.5)
    assert m.bpm() == 0.0
    m.tap(1.0)
    assert abs(m.bpm() - 120.0) < 1e-9
    assert abs(m.taps_per_second() - 2.0) < 1e-9


def test_meter_idle_reset_and_window():
    m = TapSpeedMeter(max_taps=4, idle_reset=3.0)
    for i in range(10):
        m.tap(i * 0.5)
    assert m.tap_count() == 4  # only the last 4 kept
    m.tap(100.0)  # long pause -> new measurement
    assert m.tap_count() == 1


def test_default_bindings_unique():
    # Build an id per binding (key code or mouse button) and check no two
    # default actions share one.
    ids = []
    bindings = DEFAULTS["bindings"]
    for action in bindings:
        b = bindings[action]
        if b["type"] == "mouse":
            ids.append("mouse:" + b["button"])
        else:
            ids.append("vk:" + str(b["vk"]))
    assert len(ids) == len(set(ids))
    assert bindings["smudge"]["name"] == "R" and bindings["smudge"]["vk"] == ord("R")
    assert bindings["tap"] == {"type": "mouse", "button": "left", "name": "Left click"}
