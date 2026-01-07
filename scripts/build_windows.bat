@echo off
REM ============================================================
REM PDF Extractor - Windows Build Script
REM ============================================================
REM
REM Prerequisites:
REM   - Python 3.10+ installed and in PATH
REM   - Inno Setup 6+ (optional, for installer)
REM
REM Usage:
REM   build_windows.bat          - Build executable only
REM   build_windows.bat installer - Build executable + installer
REM
REM ============================================================

setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo   PDF Extractor - Windows Build
echo ============================================================
echo.

REM Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo         Download from: https://www.python.org/downloads/
    exit /b 1
)

echo [OK] Python found
python --version

REM Create/activate virtual environment
if not exist "venv" (
    echo.
    echo [STEP] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        exit /b 1
    )
)

echo [STEP] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo.
echo [STEP] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    exit /b 1
)

REM Ask about model bundling
echo.
set /p BUNDLE_MODELS="Bundle AI models for offline use? (y/N): "
if /i "%BUNDLE_MODELS%"=="y" (
    echo.
    echo [STEP] Downloading AI models (this may take several minutes)...
    python scripts/download_models.py
    if errorlevel 1 (
        echo [WARNING] Model download failed. App will download on first run.
    )
)

REM Build with PyInstaller
echo.
echo [STEP] Building application with PyInstaller...
echo         This may take 5-10 minutes...
echo.

pyinstaller build/pdfextractor.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed
    exit /b 1
)

echo.
echo [OK] Build complete!
echo     Output: dist\PDF Extractor.exe

REM Check if installer requested
if /i "%1"=="installer" (
    echo.
    echo [STEP] Creating installer...

    REM Try to find Inno Setup
    set "ISCC="
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
        set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    )
    if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
        set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
    )

    if "!ISCC!"=="" (
        echo [WARNING] Inno Setup not found. Skipping installer creation.
        echo           Download from: https://jrsoftware.org/isinfo.php
    ) else (
        "!ISCC!" build\installer_windows.iss
        if errorlevel 1 (
            echo [ERROR] Installer creation failed
        ) else (
            echo [OK] Installer created: dist\PDF_Extractor_Setup_1.0.0.exe
        )
    )
)

echo.
echo ============================================================
echo   Build Summary
echo ============================================================
echo.
echo   Executable: dist\PDF Extractor.exe
if exist "dist\PDF_Extractor_Setup_*.exe" (
    echo   Installer:  dist\PDF_Extractor_Setup_1.0.0.exe
)
echo.
echo   To run: dist\"PDF Extractor.exe"
echo.
echo ============================================================

pause
