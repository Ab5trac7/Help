#!/bin/bash
# Double-click this ONCE to install Click Bot.
cd "$(dirname "$0")"
echo "Setting up Click Bot..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python isn't installed. A window may pop up offering to install"
  echo "'command line developer tools' - click Install, then run this again."
  xcode-select --install 2>/dev/null
  read -p "Press Enter to close."
  exit 1
fi
python3 -m venv .venv && \
  .venv/bin/pip install --quiet --upgrade pip && \
  .venv/bin/pip install --quiet pyautogui pillow opencv-python-headless
if [ $? -eq 0 ]; then
  echo ""
  echo "All set! Next: give Terminal permission to control your Mac (see README)."
else
  echo ""
  echo "Something went wrong during setup. Scroll up to see the error."
fi
read -p "Press Enter to close."
