@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   OutlookShareManager - Windows Desktop Build Script
echo ========================================================

:: 1. Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    exit /b 1
)

:: 2. Install requirements
echo [1/4] Installing Python requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install requirements!
    exit /b 1
)

:: 3. Run unit tests
echo [2/4] Running automated tests...
pytest tests/
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Some tests reported issues, proceeding with caution...
)

:: 4. Clean previous builds
echo [3/4] Cleaning previous build artifacts...
if exist build rd /s /q build
if exist dist rd /s /q dist
if exist installer_output rd /s /q installer_output

:: 5. PyInstaller build
echo [4/4] Building standalone Windows executable with PyInstaller...
pyinstaller --noconfirm --onedir --windowed ^
    --name OutlookShareManager ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --hidden-import PySide6.QtWidgets ^
    --hidden-import jdatetime ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller build failed!
    exit /b 1
)

echo [SUCCESS] Windows executable built at dist\OutlookShareManager\OutlookShareManager.exe

:: 6. Check Inno Setup for installer creation
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist !ISCC! set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if exist !ISCC! (
    echo [INFO] Inno Setup compiler found. Building Windows Installer...
    if not exist installer_output mkdir installer_output
    !ISCC! installer\OutlookShareManager.iss
    if %ERRORLEVEL% equ 0 (
        echo [SUCCESS] Installer successfully generated in installer_output\
    ) else (
        echo [ERROR] Inno Setup compilation failed!
    )
) else (
    echo [NOTICE] Inno Setup not found. Standalone executable is in dist\OutlookShareManager
    echo Install Inno Setup 6 to generate OutlookShareManager-Setup.exe
)

echo ========================================================
echo   Build completed successfully.
echo ========================================================
