@echo off
REM ============================================
REM OpTrade Development Startup Script
REM Starts FastAPI backend + Vite frontend dev server
REM ============================================

echo Starting OpTrade Development Environment...

REM Start FastAPI backend
echo [1/2] Starting FastAPI backend on http://127.0.0.1:8000 ...
start "OpTrade Backend" cmd /c "cd /d E:\MyWork\GitHubProjects\OpTrade && python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

REM Wait a moment for backend to initialize
timeout /t 2 /nobreak >nul

REM Start Vite frontend dev server
echo [2/2] Starting Vite frontend on http://127.0.0.1:3000 ...
start "OpTrade Frontend" cmd /c "cd /d E:\MyWork\GitHubProjects\OpTrade\frontend && npm run dev"

echo.
echo ============================================
echo OpTrade is starting:
echo   Backend:  http://127.0.0.1:8000
echo   Frontend: http://127.0.0.1:3000
echo   API Docs: http://127.0.0.1:8000/docs
echo ============================================
echo.
echo Press any key to exit this window (servers continue running)...
pause >nul
