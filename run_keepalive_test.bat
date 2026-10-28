@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1

rem TEST VERSION: acts after 5 seconds without input, then every 10 seconds.
rem Use run_keepalive.bat for the real overnight run.

rem The script lists open Colab windows at start and asks which one to keep alive.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH.
    pause
    exit /b 1
)
python -c "import pyautogui, pygetwindow" >nul 2>nul
if errorlevel 1 python -m pip install -r requirements.txt

python colab_keepalive.py --idle-sec 5 --every-sec 10 %*
pause
