@echo off
echo ==========================================
echo  Launching Michael AI God Mode v2.0
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
echo Browser will open automatically at http://127.0.0.1:8000/app
echo.

python backend\main.py

pause
