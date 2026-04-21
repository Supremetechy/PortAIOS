@echo off
REM Build PortAIOS.exe on Windows.
REM Run from the project root:
REM     installer\windows\build.bat
REM
REM Optional env vars:
REM   PORTAIOS_MAKE_INSTALLER=1   - also run Inno Setup to produce an installer
REM   PORTAIOS_INCLUDE_TTS=1      - bundle heavy TTS deps

setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0..\.."
pushd "%PROJECT_ROOT%"

echo ==^> PortAIOS Windows build
echo     Project root: %CD%

REM 1. Build venv
set "VENV=%CD%\.build-venv"
if not exist "%VENV%" (
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo Failed to create venv. Install Python 3.10+ from python.org.
        exit /b 1
    )
)
call "%VENV%\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
python -m pip install -r installer\requirements-build.txt
if errorlevel 1 exit /b 1

REM 2. Icons — .ico must exist; generate on macOS ahead of time and commit it,
REM    or install Pillow here and regenerate.
if not exist "installer\icons\PortAIOS.ico" (
    echo PortAIOS.ico missing. Run installer\icons\generate_icons.sh on macOS first, or install Pillow and regenerate.
    exit /b 1
)

REM 3. Clean previous build
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM 4. PyInstaller
pyinstaller installer\PortAIOS.spec --noconfirm --clean
if errorlevel 1 exit /b 1

if not exist "dist\PortAIOS\PortAIOS.exe" (
    echo Build failed — PortAIOS.exe not produced
    exit /b 1
)

echo ==^> Built: dist\PortAIOS\PortAIOS.exe

REM 5. Optional Inno Setup installer
if "%PORTAIOS_MAKE_INSTALLER%"=="1" (
    where iscc >nul 2>nul
    if errorlevel 1 (
        echo Inno Setup ^(iscc^) not found on PATH. Install from https://jrsoftware.org/isinfo.php
        exit /b 1
    )
    iscc installer\windows\installer.iss
    if errorlevel 1 exit /b 1
    echo ==^> Built installer in dist\
)

echo ==^> Done. Ship: dist\PortAIOS\
popd
endlocal
