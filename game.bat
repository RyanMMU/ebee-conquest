@echo off
setlocal

title Ebee Conquest Launcher
color 0B

cd /d "%~dp0"

echo ==========================================
echo        Ebee Conquest Launcher
echo ==========================================
echo.

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not added to PATH.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv

    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call ".venv\Scripts\activate.bat"

echo Updating pip...
python -m pip install --upgrade pip

if exist "requirements.txt" (
    echo Installing dependencies...
    python -m pip install -r requirements.txt

    if errorlevel 1 (
        echo ERROR: Dependency installation failed.
        pause
        exit /b 1
    )
) else (
    echo WARNING: requirements.txt not found. Skipping dependencies.
)

if not exist "main.py" (
    echo ERROR: main.py not found.
    pause
    exit /b 1
)

echo.
echo Launching Ebee Conquest...
echo ==========================================
echo.

python main.py

echo.
if errorlevel 1 (
    echo Ebee Conquest crashed or exited with an error.
) else (
    echo Ebee Conquest closed successfully.
)

pause
endlocal