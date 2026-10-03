#!/bin/bash
# Double-click this to run one of your recipes.
cd "$(dirname "$0")"
.venv/bin/python clickbot.py
read -p "Press Enter to close."
