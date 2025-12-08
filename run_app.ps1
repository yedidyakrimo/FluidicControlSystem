# Activate virtual environment and run the application
# Bypass Execution Policy for this script
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
& .\venv\Scripts\Activate.ps1
python main_app.py

