@echo off
echo ==========================================
echo  Michael AI - Quick Setup
echo ==========================================
echo.

echo [1/2] Recreating virtual environment...
py -m venv .venv --clear

echo [2/2] Installing dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install fastapi uvicorn pyautogui python-multipart pydantic psutil send2trash keyboard Pillow

echo.
echo ==========================================
echo  Setup Complete!
echo ==========================================
echo.
echo To run Michael AI, use: run_michael.bat
echo.
pause
