@echo off
rem Launches the Text to Speech GUI. Double-click this file to start it.
cd /d "%~dp0"

rem Check required packages first, so a missing dependency shows a message
rem instead of a window that silently never opens.
python -c "import edge_tts, pygame" >nul 2>nul
if errorlevel 1 (
    echo Missing dependencies. Run this command once:
    echo.
    echo     python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

start "" pythonw tts_gui.py
