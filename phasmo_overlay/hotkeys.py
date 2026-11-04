"""Global hotkeys (work while the game window is focused).

Why pynput: tkinter only sees keys when its own window has focus, but
you'll be in the game. pynput installs a Windows low-level keyboard and
mouse hook, so it sees every key press system-wide. It only *listens*:
the key still reaches the game, and it never touches the game itself.

Threads: pynput calls our callbacks on its own background thread.
tkinter is not thread-safe (only the main thread may touch widgets), so
the callbacks just put small messages on a queue.Queue, and the UI
thread reads that queue every few milliseconds. This is the usual,
safe way to pass events from a worker thread to a tkinter app.
"""

import queue
import time

from pynput import keyboard, mouse

# Friendly names for keys that have no printable character.
VK_NAMES = {
    8: "Backspace", 9: "Tab", 13: "Enter", 19: "Pause", 20: "CapsLock",
    32: "Space", 33: "PageUp", 34: "PageDown", 35: "End", 36: "Home",
    37: "Left", 38: "Up", 39: "Right", 40: "Down", 45: "Insert", 46: "Delete",
    96: "Num0", 97: "Num1", 98: "Num2", 99: "Num3", 100: "Num4",
    101: "Num5", 102: "Num6", 103: "Num7", 104: "Num8", 105: "Num9",
    106: "Num*", 107: "Num+", 109: "Num-", 110: "Num.", 111: "Num/",
    144: "NumLock", 145: "ScrollLock",
}
for _i in range(24):
    VK_NAMES[112 + _i] = "F" + str(_i + 1)  # vk 112 = F1 ... 135 = F24

MOUSE_NAMES = {"middle": "Mouse3", "x1": "Mouse4", "x2": "Mouse5"}

# Left and right click can't be bound: the game needs them, and you need
# left click to use the settings window.
BLOCKED_MOUSE = ("left", "right")


def key_to_binding(key):
    """Turn a pynput key object into our binding dict."""
    vk = None
    name = None
    if isinstance(key, keyboard.Key):
        # Special keys (F6, Space, Shift...). key.value is a KeyCode.
        vk = key.value.vk
        name = key.name.capitalize()
    else:
        vk = key.vk
        if key.char is not None and key.char.isprintable() and key.char != " ":
            name = key.char.upper()
    if vk is not None and vk in VK_NAMES:
        name = VK_NAMES[vk]
    if name is None:
        name = "Key " + str(vk)
    return {"type": "key", "vk": vk, "name": name}


def binding_id(binding):
    """A short string that identifies a binding, used to compare them.

    Keys are compared by vk code, not by character, because the character
    changes with Shift/Ctrl (e.g. '1' vs '!') but the physical key's vk
    code does not.
    """
    if binding is None:
        return None
    if binding["type"] == "mouse":
        return "mouse:" + binding["button"]
    if binding.get("vk") is not None:
        return "vk:" + str(binding["vk"])
    return "name:" + binding.get("name", "")


class HotkeyListener:
    def __init__(self):
        self.events = queue.Queue()
        self.lookup = {}       # binding_id -> action name
        self.held = set()      # binding_ids currently held down
        self.capturing = False
        self.kb = None
        self.ms = None

    def set_bindings(self, bindings):
        lookup = {}
        for action in bindings:
            lookup[binding_id(bindings[action])] = action
        self.lookup = lookup  # one assignment, so the other thread never sees a half-built dict

    def start(self):
        self.kb = keyboard.Listener(on_press=self._on_key_down, on_release=self._on_key_up)
        self.ms = mouse.Listener(on_click=self._on_click)
        self.kb.daemon = True
        self.ms.daemon = True
        self.kb.start()
        self.ms.start()

    def stop(self):
        if self.kb is not None:
            self.kb.stop()
        if self.ms is not None:
            self.ms.stop()

    def begin_capture(self):
        """The next key or mouse button pressed is sent as a 'capture'
        event instead of triggering an action (used for rebinding)."""
        self.capturing = True

    # ---- callbacks (run on pynput's thread) ----

    def _press(self, binding):
        t = time.perf_counter()  # timestamp here, as close to the real press as possible
        bid = binding_id(binding)

        if self.capturing:
            self.capturing = False
            if binding["type"] == "key" and binding.get("vk") == 27:  # Esc cancels
                self.events.put(("capture", None, t))
            else:
                self.events.put(("capture", binding, t))
            self.held.add(bid)  # so its release doesn't fire an action
            return

        # Windows repeats key-down events while a key is held. We only want
        # the first one, otherwise holding the tap key would add fake taps.
        if bid in self.held:
            return
        self.held.add(bid)

        action = self.lookup.get(bid)
        if action is not None:
            self.events.put(("down", action, t))

    def _release(self, binding):
        t = time.perf_counter()
        bid = binding_id(binding)
        was_held = bid in self.held
        self.held.discard(bid)
        action = self.lookup.get(bid)
        if action is not None and was_held:
            self.events.put(("up", action, t))

    def _on_key_down(self, key):
        try:
            self._press(key_to_binding(key))
        except Exception as e:  # never let an error kill the hook thread
            print("key error:", e)

    def _on_key_up(self, key):
        try:
            self._release(key_to_binding(key))
        except Exception as e:
            print("key error:", e)

    def _on_click(self, x, y, button, pressed):
        name = button.name
        if name in BLOCKED_MOUSE:
            return
        binding = {"type": "mouse", "button": name, "name": MOUSE_NAMES.get(name, name)}
        try:
            if pressed:
                self._press(binding)
            else:
                self._release(binding)
        except Exception as e:
            print("mouse error:", e)
