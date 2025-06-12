@echo off
:: ============================================================================
::  Batch file to run the DraftKings API Scraper
::
::  This script will:
::  1. Check for a Python virtual environment ('venv').
::  2. Create the virtual environment if it doesn't exist.
::  3. Activate the virtual environment.
::  4. Install/update required packages from requirements.txt.
::  5. Run the main Python GUI application.
:: ============================================================================

TITLE DraftKings API Scraper Launcher

:: Check for Python installation
echo Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not found in your system's PATH.
    echo Please install Python 3 and try again.
    pause
    exit /b 1
)
echo Python found.

:: Set the name of the virtual environment directory
set VENV_DIR=venv

:: Check if the virtual environment directory exists
echo Checking for virtual environment...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Virtual environment not found. Creating one now...
    echo This may take a moment.
    
    :: Create the virtual environment
    python -m venv %VENV_DIR%
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create the virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
) else (
    echo Virtual environment found.
)

:: Activate the virtual environment
echo Activating the virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

:: Check for requirements.txt before attempting to install
if not exist "requirements.txt" (
    echo WARNING: requirements.txt not found. Skipping package installation.
) else (
    :: Ensure pip is up-to-date in the virtual environment
    echo Ensuring pip is up-to-date...
    python -m pip install --upgrade pip
    if %errorlevel% neq 0 (
        echo WARNING: Failed to upgrade pip. Continuing with installation...
    )

    :: Install dependencies from requirements.txt using the venv's python
    echo Installing/updating required packages...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install required packages. Please check your internet connection and the requirements.txt file.
        pause
        exit /b 1
    )
    echo Packages are up to date.
)


:: Run the Python script
echo Launching the application...
python dk_api_gui_explorer.py

echo.
echo Application has been closed.
pause
