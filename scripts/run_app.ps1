# Activate virtual environment and run the application
# Bypass Execution Policy for this script
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $scriptPath "..")
& .\venv\Scripts\Activate.ps1
python main_app.py

