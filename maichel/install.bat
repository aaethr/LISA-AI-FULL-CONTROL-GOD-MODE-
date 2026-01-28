@echo off
echo ==========================================
echo  Installing Michael AI God Mode
echo ==========================================
echo.

echo [1/3] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Virtual environment not found!
    echo Please run this from the maichel directory.
    pause
    exit /b 1
)

echo [2/3] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    echo Please check your Python installation.
    pause
    exit /b 1
)

echo [3/3] Installation complete!
echo.
echo ==========================================
echo  Michael AI God Mode is ready!
echo ==========================================
echo.
echo To run Michael AI, use: python backend\main.py
echo.
pause
