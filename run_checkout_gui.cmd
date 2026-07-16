@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 chatgpt_checkout_gui.py
) else (
    python chatgpt_checkout_gui.py
)
if errorlevel 1 pause
