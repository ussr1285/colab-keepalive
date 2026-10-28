@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1

rem Part of the Colab window title to keep alive (the notebook name).
rem Use " - Colab" to target the first Colab window found.
set "TITLE=Colab_L4_TTS_batch"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH.
    pause
    exit /b 1
)
python -c "import pyautogui, pygetwindow" >nul 2>nul
if errorlevel 1 python -m pip install -r requirements.txt

python colab_keepalive.py --title "%TITLE%" %*
pause
