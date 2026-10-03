# Click Bot (free, for macOS)

Makes your Mac repeat the same clicks and typing in any app, as many times as you want.
You write the steps in a plain text file. No coding needed.

```
open Notes
click 500 80
type groceries
press enter
click image tick.png
```

## One-time setup (about 5 minutes)

1. **Download** this folder to your Mac (on GitHub: green **Code** button → **Download ZIP**, then double-click the zip).
2. **Double-click `setup.command`.**
   - If macOS says it "can't be opened": **right-click** it → **Open** → **Open**.
   - If it asks to install "command line developer tools", click **Install**, wait, then double-click `setup.command` again.
3. **Give permission to control the Mac.** Open **System Settings → Privacy & Security** and switch **Terminal** on in both:
   - **Accessibility** (needed for clicking and typing)
   - **Screen & System Audio Recording** (only needed for `click image ...`)

   If Terminal isn't in the list, press **+** and pick it from Applications → Utilities. Quit and reopen Terminal after this.

## Every day use

| To... | Do this |
|---|---|
| Run a recipe | Double-click **`run.command`**, pick a number, say how many times |
| Find where to click | Double-click **`capture.command`** |
| Make a new recipe | Copy a file in `recipes/`, rename it, edit it in TextEdit |
| See all commands | Open **`CHEATSHEET.txt`** |
| **Emergency stop** | Slam the mouse into the **top-left corner** of the screen |

## Making your own recipe (search bar → type → tick example)

1. Open the app you want to automate and set it up the way it'll be when the bot starts.
2. Double-click `capture.command`.
3. Press **Enter**, then within 3 seconds hover over the **search bar** and hold still.
   It prints a line like `click 512 84`. Copy it.
4. Do the same for the **tick box**. Tip: instead of pressing just Enter, type a name like
   `tick` and press Enter: it saves a small picture to `images/tick.png` and prints
   `click image tick.png`.
5. Duplicate `recipes/example-search-and-tick.txt`, rename it (e.g. `my-search.txt`) and
   replace the lines with yours. Change the word after `type` to whatever you want to search.
6. Double-click `run.command` and pick your recipe.

Swapping what gets clicked = swapping one line. Want several different routines? Make one
`.txt` per routine in `recipes/`; `run.command` lets you choose.

### Numbers or pictures?

- **`click 500 300`** is simple but breaks if the window moves or changes size.
  Keep the app window in the same place (e.g. maximized).
- **`click image tick.png`** finds the picture wherever it is on screen (waits up to 10s for it).
  More reliable, as long as the thing looks the same each time. If the bot can't find it,
  re-capture the picture so it contains *only* the button/box, not changing text around it.

## Troubleshooting

- **Nothing gets clicked/typed** → Terminal is missing the Accessibility permission (step 3).
- **"Couldn't see images/... on screen"** → missing Screen Recording permission, or the item
  looks different. Re-capture the picture.
- **It clicks too fast / before the app is ready** → add `wait 1` lines between steps.
- **"Permission denied" on the .command files** → open Terminal, type `chmod +x ` (with a
  space), drag the click-bot folder's `.command` files into the window, press Enter.

## Other free options (for reference)

- **Shortcuts app** (built in): great for opening apps/files, but can't click arbitrary spots.
- **Automator / AppleScript** (built in): can click buttons by name in apps that support it,
  but much fiddlier to write.
- **Hammerspoon** (free): powerful, but needs Lua code.
- Keyboard Maestro / BetterTouchTool do this with a GUI, but they're paid.
