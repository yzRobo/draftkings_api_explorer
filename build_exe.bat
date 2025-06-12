@echo off
:: ============================================================================
::  Batch file to build a single executable and clean up build files
::
::  This script will:
::  1. Activate the Python virtual environment ('venv').
::  2. Install/update PyInstaller.
::  3. Run PyInstaller to bundle the script and data files into one .exe.
::  4. Clean up the temporary build folder and .spec file upon success.
:: ============================================================================

TITLE DraftKings API Scraper Builder

:: Set the name of the virtual environment directory
set VENV_DIR=venv
set SPEC_FILE=dk_api_gui_explorer.spec

:: Check if the virtual environment exists
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found.
    echo Please run the 'run_scraper.bat' file at least once to create it before building.
    pause
    exit /b 1
)

:: Activate the virtual environment
echo Activating the virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

:: Install PyInstaller
echo Checking for PyInstaller and installing if necessary...
python -m pip install pyinstaller
if %errorlevel% neq 0 (
    echo ERROR: Failed to install PyInstaller.
    pause
    exit /b 1
)

echo.
echo Starting the build process... This may take a few minutes.
echo.

:: Run PyInstaller
:: --onefile: Bundles everything into a single executable.
:: --windowed: Prevents a console window from appearing when the GUI is run.
:: --add-data: Includes necessary data files (like your JSON reference and config).
:: The syntax is "source_file;destination_in_bundle"
pyinstaller --onefile --windowed --add-data "id_reference.json;." --add-data "config.json;." "dk_api_gui_explorer.py"

:: Check if the build was successful
if %errorlevel% neq 0 (
    echo.
    echo ERROR: The build process failed. Please review the messages above.
    echo Cleanup will be skipped.
    pause
    exit /b 1
)

echo.
echo Build successful. Cleaning up temporary files...

:: Clean up build files
if exist "build" (
    echo Removing 'build' directory...
    rmdir /s /q build
)
if exist "%SPEC_FILE%" (
    echo Removing '%SPEC_FILE%'...
    del "%SPEC_FILE%"
)

echo.
echo ==================================================================
echo      CLEANUP COMPLETE!
echo ==================================================================
echo.
echo The final executable file can be found in the 'dist' folder:
echo.
echo     %cd%\dist\dk_api_gui_explorer.exe
echo.
echo You can share this single .exe file with others.
echo.

pause
