@echo off
REM ============================================
REM OpTrade Desktop Build Script
REM Builds frontend and packages with PyInstaller
REM ============================================

echo Building OpTrade Desktop...

echo [1/2] Building frontend...
cd /d "%~dp0\..\frontend"
call npm run build
if errorlevel 1 (
    echo Frontend build failed!
    pause
    exit /b 1
)

echo.
echo [2/2] Packaging with PyInstaller...
cd /d "%~dp0\.."

REM playwright (~200MB with browser binaries) is excluded.
REM The chinamoney auto-crawl feature will be unavailable,
REM but manual XLSX upload (parse_xlsx) still works via openpyxl.
pyinstaller ^
  --name "OpTrade" ^
  --windowed ^
  --icon "frontend/public/favicon.ico" ^
  --add-data "frontend/dist;frontend/dist" ^
  --add-data "frontend/public/favicon.ico;frontend/public/favicon.ico" ^
  --paths "backend" ^
  --collect-submodules "app" ^
  --collect-submodules "uvicorn" ^
  --exclude-module playwright ^
  --clean ^
  --noconfirm ^
  "backend/app/desktop/window.py"

echo.
echo Build complete. Output: dist\OpTrade\
echo.
pause
