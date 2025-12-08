@echo off
REM Run application directly using venv Python (no activation needed)
echo Running application from virtual environment...
venv\Scripts\python.exe main_app.py
if errorlevel 1 (
    echo.
    echo Application exited with error
    pause
)


