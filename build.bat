@echo off
echo ═══════════════════════════════════════════════════════
echo   KYRA AI Assistant — Build Installer
echo ═══════════════════════════════════════════════════════
echo.

set ROOT=%~dp0
cd /d "%ROOT%"

REM ── Step 1: PyInstaller backend ─────────────────────────────────────────────
echo [1/3] Building Python backend with PyInstaller...
cd backend
call "%ROOT%.venv\Scripts\activate.bat"
pip install pyinstaller -q
pyinstaller kyra_backend.spec --noconfirm --clean
if errorlevel 1 (
    echo ERROR: PyInstaller failed!
    pause
    exit /b 1
)
cd ..

REM ── Step 2: Build React/Vite frontend ───────────────────────────────────────
echo.
echo [2/3] Building React frontend...
cd frontend
call npm run build
if errorlevel 1 (
    echo ERROR: Frontend build failed!
    pause
    exit /b 1
)

REM ── Step 3: Package with electron-builder ───────────────────────────────────
echo.
echo [3/3] Packaging with electron-builder...
call npm run electron:build
if errorlevel 1 (
    echo ERROR: electron-builder failed!
    pause
    exit /b 1
)

echo.
echo ═══════════════════════════════════════════════════════
echo   BUILD COMPLETE!
echo   Installer saved to: C:\Users\srira\Downloads\KYRA_App
echo ═══════════════════════════════════════════════════════
pause
