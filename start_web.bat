@echo off
title Text to Speech Web Studio
echo =====================================================================
echo  Launching Text to Speech Studio (Web Edition) ...
echo =====================================================================
python web_studio.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Web Studio failed to launch. Ensure Python 3.10+ and edge-tts are installed:
    echo     pip install -r requirements.txt
    echo.
    pause
)
