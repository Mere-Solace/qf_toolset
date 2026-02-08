@echo off
title Finance Dev Servers

echo ============================================
echo   Finance Dev Environment Launcher
echo ============================================
echo.

:: Kill any stale processes on ports 8000 and 3000
echo Checking for stale processes on ports 8000 and 3000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do echo Killing stale process on port 8000 (PID %%a)... & taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do echo Killing stale process on port 3000 (PID %%a)... & taskkill /PID %%a /F >nul 2>&1
timeout /t 1 /nobreak >nul

:: Check .env exists
if not exist .env (
    echo [ERROR] No .env file found. Create one with your FRED_API_KEY.
    echo Example: echo FRED_API_KEY=your_key_here ^> .env
    pause
    exit /b 1
)

:: Check venv exists
if not exist .venv\Scripts\python.exe (
    echo [ERROR] Python virtual environment not found at .venv\
    echo Run: python -m venv .venv ^&^& .venv\Scripts\pip install -e ".[dev]"
    pause
    exit /b 1
)

echo Starting backend (FastAPI on :8000)...
start "Finance Backend" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.main:app --reload --reload-dir backend --port 8000"

echo Waiting for backend to be ready...
set /a attempts=0
:wait
set /a attempts+=1
if %attempts% gtr 30 (
    echo [ERROR] Backend failed to start after 60 seconds. Check the backend window for errors.
    pause
    exit /b 1
)
timeout /t 2 /nobreak >nul
powershell -Command "try { (Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing -TimeoutSec 2).StatusCode } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto wait

echo Backend is up!
echo Starting frontend (Vite on :3000)...
start "Finance Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================
echo   Both servers running:
echo     Backend:  http://localhost:8000
echo     API docs: http://localhost:8000/docs
echo     Frontend: http://localhost:3000
echo     Logs:     logs/app.log
echo ============================================
echo.
echo Close this window or press Ctrl+C. Servers run in their own windows.
