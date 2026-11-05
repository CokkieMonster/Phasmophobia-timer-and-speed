# Phasmophobia-timer-and-speed

A small always-on-top overlay for Phasmophobia (Windows) with:

- **Smudge timer**: counts up after you smudge, with markers at **60 s** (Demon can hunt), **90 s** (most ghosts can hunt) and **180 s** (Spirit can hunt).
- **Hunt cooldown timer**: counts up after a hunt ends, with markers at **20 s** (Demon) and **25 s** (any ghost).
- **Ghost speed**: tap a key along with the ghost's footsteps and it shows taps/sec and the estimated speed in m/s (1.7 m/s = normal ghost).

It only listens for key presses. It never reads or changes the game's files or memory.

## Download (no Python needed)

1. Go to the [**Releases page**](../../releases/latest) and download `PhasmoTimer-vX.Y.Z-windows.zip`.
2. Right-click the zip, choose **Extract All**, then open the extracted `PhasmoTimer` folder.
3. Run **PhasmoTimer.exe**.
   If Windows shows **"Windows protected your PC"**, click **More info**, then **Run anyway**.
   The warning appears because the app isn't code-signed (a certificate costs money), not because anything was detected.
4. In Phasmophobia: **Options → Video → Display Mode → Windowed Borderless**.
   True fullscreen draws over everything, so the overlay can't show on top of it.

Keep `PhasmoTimer.exe` inside its folder: it needs the `_internal` folder next to it.

## Run from source

1. Install Python 3.10+ from python.org (tick **"Add Python to PATH"**).
2. In this folder:
   ```
   pip install -r requirements.txt
   python run.py
   ```
   Use `pythonw run.py` to run it without a console window.

To build the app folder yourself, run `build.bat`. The result is `dist\PhasmoTimer\PhasmoTimer.exe`.

## Controls (defaults, all rebindable)

| Key | Action |
|-----|--------|
| R   | Smudge timer: press = start, press again = stop, **hold** = clear |
| E   | Hunt cooldown timer: same as above |
| Left click | Tap once per ghost footstep |
| L   | Lock / unlock the overlay (unlocked = orange border, drag to move) |
| P   | Show / hide the overlay |
| F11 | Open settings |

These keys are only *listened to*, not blocked, so the game still receives them too.
If one clashes with a game control you use, rebind it in settings.

**Left click counts every click as a footstep tap**, including in-game clicks and clicks in other windows.
That's harmless: the speed only uses taps less than 3 s apart, so stray clicks just start a fresh measurement.
Click 3+ times in rhythm with the footsteps to get a reading.

If you ran an older version, your saved keys are kept. To get these defaults, delete
`%APPDATA%\PhasmoTimer\config.json` or rebind in settings.

While the overlay is **locked**, mouse clicks pass straight through it to the game.
While it's **unlocked** you can drag it, and right-click opens settings.

## Settings

Open with F11. Settings are saved automatically to `%APPDATA%\PhasmoTimer\config.json`.

- **Keybinds**: click a button and press any key, or a mouse button (Left click, Mouse3/Mouse4/Mouse5; right click is reserved). Esc cancels. If you pick a key another action already uses, the two actions swap keys.
- **Lobby ghost speed**: set this to your lobby's ghost speed (50 to 150 %). The m/s shown is the ghost's *base* speed, so 1.7 m/s always means a normal ghost.
- **Hold to clear**: how long to hold a timer key to clear it (default 0.6 s).
- **Taps averaged**: more taps gives a steadier number, fewer reacts faster.
- **Opacity / Size**.

## Reading the speed

- Tap at least 3 times before a number appears.
- Pausing for more than 3 s starts a new measurement.
- Blue = slower than normal (< 1.55 m/s), white = normal, red = faster (> 1.85 m/s).
- Ghosts speed up while they can see you (line of sight), so tap early in the chase or while it can't see you.

The conversion uses the formula from the
[Zero-Network Unofficial Phasmophobia Cheat Sheet](https://zero-network.net/phasmo-cheat-sheet):
`speed = BPM / (lobby_speed × (60 + 0.075 × BPM))`.

## Troubleshooting

- **Overlay doesn't appear over the game**: the game is in fullscreen. Switch to Windowed Borderless.
- **Hotkeys don't work in game**: if the game is running as administrator, the overlay must be too.
- **Wrong place / off-screen**: open settings and click *Reset position*.

## Making a release (for the maintainer)

Pushing a version tag makes GitHub build the app on a Windows machine and publish it on the Releases page:

```
git tag v1.0.0
git push origin v1.0.0
```

Progress shows in the repo's **Actions** tab. The build runs the tests first, so a broken build never gets published.
To fix a release, delete its tag and Release on GitHub, then push the tag again.

## Project layout

```
run.py                        entry point
phasmo_overlay/
  app.py                      wires hotkeys → timers/speed → overlay
  timers.py                   stopwatch + smudge/hunt markers (no UI)
  speed.py                    tap → BPM → m/s (no UI)
  hotkeys.py                  global keyboard/mouse listener (pynput)
  overlay.py                  the always-on-top, click-through window
  settings_window.py          rebinding + options
  config.py                   load/save settings
tests/test_logic.py           unit tests: python -m pytest
assets/icon.ico               app icon
.github/workflows/release.yml builds + publishes the release zip
```

## License

MIT. See [LICENSE](LICENSE).
