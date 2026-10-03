"""
Click Bot - repeat the same clicks and typing in any Mac app.

You normally don't need to touch this file.
Write your steps in a text file inside the "recipes" folder instead.
"""

import os
import subprocess
import sys
import time

try:
    import pyautogui
except ImportError:
    print("Click Bot isn't set up yet. Double-click 'setup.command' first.")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
RECIPES = os.path.join(HERE, "recipes")
IMAGES = os.path.join(HERE, "images")

# Slamming the mouse into the top-left corner of the screen stops the bot.
pyautogui.FAILSAFE = True
# Small pause after every action so apps can keep up.
pyautogui.PAUSE = 0.3

IMAGE_TIMEOUT = 10  # seconds to keep looking for an image before giving up


def screen_scale():
    """Retina screens have 2 real pixels per point; screenshots use pixels, clicks use points."""
    return pyautogui.screenshot().width / pyautogui.size().width


def find_image(name):
    path = os.path.join(IMAGES, name)
    if not os.path.exists(path):
        raise RuntimeError(f"Image not found: images/{name}")
    scale = screen_scale()
    deadline = time.time() + IMAGE_TIMEOUT
    while time.time() < deadline:
        try:
            try:
                spot = pyautogui.locateCenterOnScreen(path, confidence=0.85)
            except (NotImplementedError, TypeError):
                spot = pyautogui.locateCenterOnScreen(path)
        except pyautogui.ImageNotFoundException:
            spot = None
        if spot:
            return spot.x / scale, spot.y / scale
        time.sleep(0.5)
    raise RuntimeError(f"Couldn't see images/{name} on screen after {IMAGE_TIMEOUT} seconds")


def target(args):
    """Turn '500 300' or 'image button.png' into an x, y position."""
    if args and args[0].lower() == "image":
        return find_image(" ".join(args[1:]))
    if len(args) == 2:
        return int(args[0]), int(args[1])
    raise RuntimeError("Expected two numbers (x y) or 'image name.png'")


def type_text(text):
    if text.isascii():
        pyautogui.write(text, interval=0.03)
    else:
        # pyautogui can't type accents/emoji, so paste them instead.
        subprocess.run("pbcopy", input=text.encode("utf-8"))
        pyautogui.hotkey("command", "v")


def run_step(line):
    words = line.split()
    cmd, args = words[0].lower(), words[1:]
    rest = line.split(None, 1)[1] if len(words) > 1 else ""

    if cmd == "open":
        subprocess.run(["open", "-a", rest], check=True)
        time.sleep(1)
    elif cmd == "wait":
        time.sleep(float(rest))
    elif cmd == "click":
        pyautogui.click(*target(args))
    elif cmd == "doubleclick":
        pyautogui.doubleClick(*target(args))
    elif cmd == "rightclick":
        pyautogui.rightClick(*target(args))
    elif cmd == "move":
        pyautogui.moveTo(*target(args), duration=0.2)
    elif cmd == "type":
        type_text(rest)
    elif cmd == "press":
        pyautogui.press(rest.lower())
    elif cmd == "hotkey":
        pyautogui.hotkey(*[a.lower() for a in args])
    elif cmd == "scroll":
        pyautogui.scroll(int(rest))
    else:
        raise RuntimeError(f"Unknown command '{cmd}'")


def load_steps(path):
    steps = []
    with open(path, encoding="utf-8") as f:
        for number, raw in enumerate(f, 1):
            line = raw.strip()
            if line and not line.startswith("#"):
                steps.append((number, line))
    return steps


def run_recipe(path, times):
    steps = load_steps(path)
    name = os.path.basename(path)
    print(f"\nRunning '{name}' {times} time(s). Starting in 3 seconds...")
    print("To stop: slam the mouse into the TOP-LEFT corner of the screen.\n")
    time.sleep(3)
    for round_number in range(1, times + 1):
        if times > 1:
            print(f"--- Round {round_number} of {times} ---")
        for number, line in steps:
            print(f"  line {number}: {line}")
            try:
                run_step(line)
            except pyautogui.FailSafeException:
                print("\nStopped (mouse hit the corner).")
                return
            except Exception as error:
                print(f"\nProblem on line {number} of {name}: {error}")
                return
    print("\nDone!")


def pick_recipe():
    files = sorted(f for f in os.listdir(RECIPES) if f.endswith(".txt"))
    if not files:
        print("No recipes found. Put a .txt file in the 'recipes' folder.")
        sys.exit(1)
    print("Which recipe do you want to run?")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f[:-4]}")
    choice = input("Type a number and press Enter: ").strip()
    try:
        return os.path.join(RECIPES, files[int(choice) - 1])
    except (ValueError, IndexError):
        print("That's not one of the numbers.")
        sys.exit(1)


def ask_times():
    answer = input("How many times? (just press Enter for 1): ").strip()
    return int(answer) if answer.isdigit() and int(answer) > 0 else 1


def capture():
    print("CAPTURE MODE - find out where to click\n")
    print("  - Press Enter               -> get a position (for 'click x y')")
    print("  - Type a name, press Enter  -> also save a small picture of that spot")
    print("                                 (for 'click image name.png')")
    print("  - Type q, press Enter       -> quit")
    print("\nAfter pressing Enter you get 3 seconds to put the mouse on the spot. Hold still!\n")
    scale = screen_scale()
    while True:
        answer = input("> ").strip()
        if answer.lower() == "q":
            break
        for n in (3, 2, 1):
            print(f"  {n}...")
            time.sleep(1)
        x, y = pyautogui.position()
        if answer:
            filename = answer if answer.endswith(".png") else answer + ".png"
            # Grab a small box around the mouse (in real screen pixels).
            w, h = 60, 30
            box = (int((x - w / 2) * scale), int((y - h / 2) * scale), int(w * scale), int(h * scale))
            pyautogui.screenshot(region=box).save(os.path.join(IMAGES, filename))
            print(f"Saved images/{filename}. Copy this line into your recipe:")
            print(f"    click image {filename}\n")
        else:
            print("Copy this line into your recipe:")
            print(f"    click {x} {y}\n")


def main():
    if "--capture" in sys.argv:
        capture()
        return
    path = pick_recipe()
    run_recipe(path, ask_times())


if __name__ == "__main__":
    main()
