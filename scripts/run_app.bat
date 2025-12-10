@echo off
REM Activate virtual environment and run the application
cd /d %~dp0..
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)
python main_app.py
if errorlevel 1 (
    echo.
    echo Application exited with error
    pause
)

