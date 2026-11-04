"""Loading and saving settings (keybinds, position, speed setting...).

Settings live in %APPDATA%\\PhasmoTimer\\config.json on Windows. That
folder is used instead of the program folder because a built .exe may
sit somewhere Windows won't let it write (e.g. Program Files).
"""

import copy
import json
import os

# The things a key can be bound to. The order here is the order shown in
# the settings window.
ACTIONS = [
    ("smudge", "Smudge timer"),
    ("hunt", "Hunt cooldown timer"),
    ("tap", "Tap footstep (speed)"),
    ("lock", "Lock / unlock overlay"),
    ("hide", "Show / hide overlay"),
    ("settings", "Open settings"),
]

# A binding is a small dict:
#   {"type": "key", "vk": 82, "name": "R"}     keyboard key (vk = Windows virtual-key code)
#   {"type": "mouse", "button": "x1", "name": "Mouse4"}
# vk codes: letters use their capital ASCII code (E=69, F=70, L=76,
# P=80, R=82), F11=122. Matching by vk means Shift/Caps Lock don't matter.
DEFAULTS = {
    "bindings": {
        "smudge": {"type": "key", "vk": 82, "name": "R"},
        "hunt": {"type": "key", "vk": 69, "name": "E"},
        "tap": {"type": "key", "vk": 70, "name": "F"},
        "lock": {"type": "key", "vk": 76, "name": "L"},
        "hide": {"type": "key", "vk": 80, "name": "P"},
        "settings": {"type": "key", "vk": 122, "name": "F11"},
    },
    "speed_modifier": 1.0,   # lobby ghost speed: 0.5 .. 1.5
    "hold_to_clear": 0.6,    # seconds a timer key must be held to clear it
    "max_taps": 12,          # taps averaged for the speed
    "opacity": 0.85,
    "scale": 1.0,            # overall size of the overlay
    "x": 40,
    "y": 40,
}


def config_path():
    base = os.environ.get("APPDATA")
    if base is None:
        base = os.path.expanduser("~")
    folder = os.path.join(base, "PhasmoTimer")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "config.json")


def load():
    """Return the saved config, with defaults filled in for anything
    missing. Filling in defaults means an older config file keeps working
    after a new setting is added in a later version."""
    cfg = copy.deepcopy(DEFAULTS)
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return cfg

    for key in saved:
        if key == "bindings":
            for action in saved["bindings"]:
                if action in cfg["bindings"]:
                    cfg["bindings"][action] = saved["bindings"][action]
        elif key in cfg:
            cfg[key] = saved[key]
    return cfg


def save(cfg):
    try:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except OSError as e:
        print("Could not save settings:", e)
