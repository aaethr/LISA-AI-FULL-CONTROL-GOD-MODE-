@echo off
echo ==========================================
echo  Launching LISA Personal AI
echo ==========================================
echo.

cd /d "%~dp0"

echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Virtual environment not activated!
    echo Run install.bat first!
    pause
    exit /b 1
)

echo.
echo Starting Michael AI...
echo.

python backend\main.py

pause
