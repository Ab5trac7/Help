#!/usr/bin/env python3
"""
autoclick.py - automate app clicks on macOS.

Commands:
  pos                         Show live mouse coordinates (Ctrl+C to stop).
  record FILE [--app NAME]    Record your clicks/keys into FILE (press Esc to stop).
  play FILE [--repeat N] [--speed X] [--app NAME]
                              Replay a recorded/handwritten script.
  click X Y [--app NAME] [--double] [--right]
                              Click once at screen coordinates.
  button APP "Button name" [--window N]
                              Click a button by its name (no coordinates needed).
  menu APP "Menu" "Item" ["Submenu item" ...]
                              Click a menu-bar item, e.g. menu Safari File "New Window".

Emergency stop during playback: slam the mouse into the top-left screen corner.

Requires: Python 3.9+, `pip3 install pynput`, and Accessibility permission for
your terminal (System Settings > Privacy & Security > Accessibility, and also
Input Monitoring for `record`).
"""
import argparse
import json
import subprocess
import sys
import time


# ---------- helpers ----------

def need_pynput():
    try:
        from pynput import keyboard, mouse  # noqa: F401
        return keyboard, mouse
    except ImportError:
        sys.exit("pynput is not installed. Run:  pip3 install pynput")


def osascript(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        msg = r.stderr.strip()
        if "not allowed assistive access" in msg or "-1719" in msg or "-25211" in msg:
            msg += ("\n-> Give your terminal Accessibility permission: System Settings > "
                    "Privacy & Security > Accessibility.")
        sys.exit(f"AppleScript error: {msg}")
    return r.stdout.strip()


def as_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def activate(app):
    if app:
        osascript(f"tell application {as_str(app)} to activate")
        time.sleep(0.6)


BUTTONS = {"left": "left", "right": "right", "middle": "middle"}


class Failsafe(Exception):
    pass


def check_failsafe(m):
    x, y = m.position
    if x <= 2 and y <= 2:
        raise Failsafe()


# ---------- commands ----------

def cmd_pos(_):
    _, mouse = need_pynput()
    m = mouse.Controller()
    print("Move the mouse; Ctrl+C to stop.")
    try:
        while True:
            x, y = m.position
            print(f"\rx={int(x):5d}  y={int(y):5d}   ", end="", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()


def cmd_click(a):
    _, mouse = need_pynput()
    activate(a.app)
    m = mouse.Controller()
    m.position = (a.x, a.y)
    time.sleep(0.05)
    btn = mouse.Button.right if a.right else mouse.Button.left
    m.click(btn, 2 if a.double else 1)


def cmd_record(a):
    keyboard, mouse = need_pynput()
    activate(a.app)
    steps = []
    last = [time.time()]

    def gap():
        now = time.time()
        d = round(now - last[0], 3)
        last[0] = now
        return d

    def on_click(x, y, button, pressed):
        if pressed:
            steps.append({"type": "click", "x": int(x), "y": int(y),
                          "button": button.name, "wait": gap()})
            print(f"  click {button.name} at ({int(x)}, {int(y)})")

    def on_press(key):
        if key == keyboard.Key.esc:
            return False
        if hasattr(key, "char") and key.char:
            steps.append({"type": "type", "text": key.char, "wait": gap()})
        else:
            steps.append({"type": "key", "key": key.name, "wait": gap()})

    print("Recording... click around. Press Esc to stop.")
    with mouse.Listener(on_click=on_click) as ml, keyboard.Listener(on_press=on_press) as kl:
        kl.join()
        ml.stop()

    # merge consecutive typed characters
    merged = []
    for s in steps:
        if s["type"] == "type" and merged and merged[-1]["type"] == "type" and s["wait"] < 1.5:
            merged[-1]["text"] += s["text"]
        else:
            merged.append(s)

    data = {"app": a.app, "steps": merged}
    with open(a.file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(merged)} steps to {a.file}")


def run_step(s, m, k, keyboard, mouse, speed):
    wait = float(s.get("wait", 0.3)) / speed
    deadline = time.time() + wait
    while time.time() < deadline:
        check_failsafe(m)
        time.sleep(min(0.05, max(0, deadline - time.time())))
    check_failsafe(m)

    t = s["type"]
    if t == "click":
        m.position = (s["x"], s["y"])
        time.sleep(0.05)
        btn = getattr(mouse.Button, BUTTONS.get(s.get("button", "left"), "left"))
        m.click(btn, int(s.get("count", 1)))
    elif t == "type":
        k.type(s["text"])
    elif t == "key":
        keys = s["key"] if isinstance(s["key"], list) else [s["key"]]
        resolved = [getattr(keyboard.Key, n, None) or n for n in keys]
        for r in resolved:
            k.press(r)
        for r in reversed(resolved):
            k.release(r)
    elif t == "scroll":
        m.scroll(int(s.get("dx", 0)), int(s.get("dy", -3)))
    elif t == "sleep":
        pass  # the wait already happened
    elif t == "activate":
        activate(s["app"])
    elif t == "button":
        click_button(s["app"], s["name"], int(s.get("window", 1)))
    elif t == "menu":
        click_menu(s["app"], s["path"])
    else:
        sys.exit(f"Unknown step type: {t}")


def cmd_play(a):
    keyboard, mouse = need_pynput()
    with open(a.file) as f:
        data = json.load(f)
    steps = data["steps"] if isinstance(data, dict) else data
    app = a.app or (data.get("app") if isinstance(data, dict) else None)
    m, k = mouse.Controller(), keyboard.Controller()
    activate(app)
    print("Playing. Emergency stop: move mouse to the top-left corner.")
    try:
        i = 0
        while a.repeat == 0 or i < a.repeat:
            i += 1
            print(f"Run {i}" + (f"/{a.repeat}" if a.repeat else ""))
            for s in steps:
                run_step(s, m, k, keyboard, mouse, a.speed)
            if a.pause:
                time.sleep(a.pause)
    except Failsafe:
        print("Stopped by failsafe (mouse in top-left corner).")
    except KeyboardInterrupt:
        print("\nStopped.")


def click_button(app, name, window=1):
    script = f'''
    tell application {as_str(app)} to activate
    delay 0.3
    tell application "System Events" to tell process {as_str(app)}
        set w to window {window}
        set hits to (every button of entire contents of w whose name is {as_str(name)} or description is {as_str(name)})
        if (count of hits) is 0 then error "No button named " & {as_str(name)}
        click item 1 of hits
    end tell'''
    osascript(script)


def click_menu(app, path):
    if len(path) < 2:
        sys.exit('menu needs at least: "Menu" "Item"')
    ref = f"menu bar item {as_str(path[0])} of menu bar 1"
    for item in path[1:]:
        ref = f"menu item {as_str(item)} of menu 1 of {ref}"
    script = f'''
    tell application {as_str(app)} to activate
    delay 0.3
    tell application "System Events" to tell process {as_str(app)}
        click {ref}
    end tell'''
    osascript(script)


def cmd_button(a):
    click_button(a.app, a.name, a.window)


def cmd_menu(a):
    click_menu(a.app, a.path)


# ---------- CLI ----------

def main(argv=None):
    p = argparse.ArgumentParser(description="Automate app clicks on macOS.",
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("pos", help="show live mouse coordinates").set_defaults(fn=cmd_pos)

    s = sub.add_parser("record", help="record clicks to a JSON file (Esc to stop)")
    s.add_argument("file")
    s.add_argument("--app", help="app to bring to the front first")
    s.set_defaults(fn=cmd_record)

    s = sub.add_parser("play", help="replay a JSON script")
    s.add_argument("file")
    s.add_argument("--repeat", type=int, default=1, help="times to repeat (0 = forever)")
    s.add_argument("--speed", type=float, default=1.0, help="2 = twice as fast")
    s.add_argument("--pause", type=float, default=0, help="seconds between repeats")
    s.add_argument("--app", help="override app to activate")
    s.set_defaults(fn=cmd_play)

    s = sub.add_parser("click", help="click at coordinates")
    s.add_argument("x", type=int)
    s.add_argument("y", type=int)
    s.add_argument("--app")
    s.add_argument("--double", action="store_true")
    s.add_argument("--right", action="store_true")
    s.set_defaults(fn=cmd_click)

    s = sub.add_parser("button", help="click a button by name")
    s.add_argument("app")
    s.add_argument("name")
    s.add_argument("--window", type=int, default=1)
    s.set_defaults(fn=cmd_button)

    s = sub.add_parser("menu", help="click a menu bar item")
    s.add_argument("app")
    s.add_argument("path", nargs="+")
    s.set_defaults(fn=cmd_menu)

    a = p.parse_args(argv)
    if a.cmd in ("play",) and a.speed <= 0:
        p.error("--speed must be > 0")
    a.fn(a)


if __name__ == "__main__":
    main()
