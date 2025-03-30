@echo off
setlocal

REM Get the directory where this batch script is located
set SCRIPT_DIR=%~dp0

REM Define paths relative to the script directory
set VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe
set GUI_SCRIPT=%SCRIPT_DIR%youtube_transcriber_gui.py

REM Check if the virtual environment's Python executable exists
if not exist "%VENV_PYTHON%" (
    echo ERROR: Python executable not found in the virtual environment!
    echo Looking for: %VENV_PYTHON%
    echo.
    echo Please make sure you have:
    echo 1. Created the virtual environment (e.g., python -m venv .venv)
    echo 2. Installed requirements (e.g., pip install -r requirements.txt)
    echo See README.md for setup instructions.
    pause
    exit /b 1
)

REM Check if the main GUI script exists
if not exist "%GUI_SCRIPT%" (
    echo ERROR: The GUI script youtube_transcriber_gui.py was not found!
    echo Looking for: %GUI_SCRIPT%
    pause
    exit /b 1
)

echo Starting YouTube Transcriber GUI...
REM Run the Python script using the virtual environment's interpreter
"%VENV_PYTHON%" "%GUI_SCRIPT%"

echo.
REM Optional: Pause if the script exits very quickly (e.g., due to an immediate error not caught by Tkinter)
REM If the GUI handles errors with message boxes, this pause might be unnecessary.
REM pause

endlocal