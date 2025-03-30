#!/bin/bash

# Get the absolute path to the directory where this script resides
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Define paths relative to the script directory
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
GUI_SCRIPT="$SCRIPT_DIR/youtube_transcriber_gui.py"

# Check if the virtual environment's Python executable exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Python executable not found in the virtual environment!" >&2
    echo "Looking for: $VENV_PYTHON" >&2
    echo "" >&2
    echo "Please make sure you have:" >&2
    echo "1. Created the virtual environment (e.g., python3 -m venv .venv)" >&2
    echo "2. Installed requirements (e.g., pip install -r requirements.txt)" >&2
    echo "See README.md for setup instructions." >&2
    # Provide a simple way to close the terminal if launched by double-click
    read -p "Press Enter to close..."
    exit 1
fi

# Check if the main GUI script exists
if [ ! -f "$GUI_SCRIPT" ]; then
    echo "ERROR: The GUI script youtube_transcriber_gui.py was not found!" >&2
    echo "Looking for: $GUI_SCRIPT" >&2
    read -p "Press Enter to close..."
    exit 1
fi


echo "Starting YouTube Transcriber GUI..."
# Execute the Python script using the virtual environment's interpreter
"$VENV_PYTHON" "$GUI_SCRIPT"

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo ""
    echo "The application exited with status code $exit_code."
    # Optional: pause only if there was an error
    # read -p "Press Enter to close..."
fi

exit $exit_code