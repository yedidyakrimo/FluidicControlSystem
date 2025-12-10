# Virtual Environment Setup

## Setup Instructions

A virtual environment has been created in the `venv/` folder with all required packages installed.

## Running the Application

### Option 1: Direct Run (Recommended - No activation needed)
```bash
scripts\run_app_direct.bat
```
This runs the application directly using the virtual environment's Python without needing to activate it.

### Option 2: Using Batch File (with activation)
```bash
scripts\run_app.bat
```

### Option 3: Using PowerShell Script
```powershell
.\scripts\run_app.ps1
```
Note: If you get Execution Policy error, the script will automatically bypass it for this session.

### Option 4: Manual Activation (Command Prompt)
```cmd
venv\Scripts\activate.bat
python main_app.py
```

### Option 5: Manual Activation (PowerShell - if Execution Policy allows)
```powershell
.\venv\Scripts\Activate.ps1
python main_app.py
```

### Option 6: Direct Python (No activation)
```bash
venv\Scripts\python.exe main_app.py
```

## Installed Packages

All packages from `requirements.txt` are installed in the virtual environment:
- customtkinter
- matplotlib
- pyserial
- nidaqmx
- mcculw
- numpy
- pyvisa
- pandas
- openpyxl
- **vapourtec** (for pump control)

## Notes

- The virtual environment is located in `venv/` folder
- Always activate the virtual environment before running the application
- The `venv/` folder should be added to `.gitignore` (if using git)

