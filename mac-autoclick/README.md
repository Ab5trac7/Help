# mac-autoclick

Automate clicks in any macOS app. You can record and replay, click by coordinates,
or click buttons and menu items by name.

## Setup (one time)

```bash
cd mac-autoclick
pip3 install pynput
```

Then open **System Settings → Privacy & Security** and add your terminal app
(Terminal, iTerm, …) to:
- **Accessibility** (needed for clicking)
- **Input Monitoring** (needed for `record`)

Quit and reopen the terminal after granting these.

## Use

```bash
# 1. Find coordinates
python3 autoclick.py pos

# 2. Record what you do in an app, press Esc when done
python3 autoclick.py record myjob.json --app "Safari"

# 3. Replay it (5 times, 2x speed, 3s between runs; --repeat 0 = forever)
python3 autoclick.py play myjob.json --repeat 5 --speed 2 --pause 3

# One-off actions
python3 autoclick.py click 500 300 --app "Finder" --double
python3 autoclick.py button "System Settings" "Done"
python3 autoclick.py menu Safari File "New Window"
```

**Emergency stop:** move the mouse into the **top-left corner** of the screen, or press Ctrl+C.

## Script format

The recorded `.json` file can be edited by hand. Each step waits `wait` seconds and then runs:

| type       | fields                                            |
|------------|---------------------------------------------------|
| `click`    | `x`, `y`, `button` (left/right), `count`          |
| `type`     | `text`                                            |
| `key`      | `key`, e.g. `"enter"` or `["cmd", "s"]`           |
| `scroll`   | `dx`, `dy`                                        |
| `sleep`    | (just waits)                                      |
| `activate` | `app`                                             |
| `button`   | `app`, `name`, `window`: click a button by name   |
| `menu`     | `app`, `path`: e.g. `["File", "Save"]`            |

See `example.json`. Name-based `button`/`menu` steps keep working when windows move.
Coordinate clicks do not.
