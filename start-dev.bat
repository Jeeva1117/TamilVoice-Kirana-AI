@echo off
chcp 65001 >nul
title TamilVoice Kirana AI - Development Launcher
cd /d "%~dp0"

echo ========================================================================
echo        TamilVoice Kirana AI - Local Development Environment
echo ========================================================================
echo.

:: Detect Python environment
set "PYTHON_CMD=python"
if exist "venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0venv\Scripts\python.exe"
    echo [*] Using virtual environment: venv
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"
    echo [*] Using virtual environment: .venv
) else (
    echo [*] Using system Python
)

:: Verify python runs
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add it to your PATH.
    pause
    exit /b 1
)

echo [*] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "TamilVoice Kirana - FastAPI Backend (Port 8000)" cmd /k "chcp 65001 >nul && cd /d ""%~dp0"" && echo ==================================================== && echo   FastAPI Backend Server running on http://127.0.0.1:8000 && echo   API Docs available at http://127.0.0.1:8000/docs && echo   Health check at http://127.0.0.1:8000/health && echo ==================================================== && ""%PYTHON_CMD%"" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo [*] Starting Frontend Static Server on http://127.0.0.1:3000 ...
start "TamilVoice Kirana - Frontend Server (Port 3000)" cmd /k "chcp 65001 >nul && cd /d ""%~dp0"" && echo ==================================================== && echo   Frontend Web Server running on http://127.0.0.1:3000 && echo ==================================================== && ""%PYTHON_CMD%"" -m http.server 3000 --directory frontend"

timeout /t 2 /nobreak >nul

echo [*] Opening application in browser: http://127.0.0.1:3000 ...
start http://127.0.0.1:3000

echo.
echo ========================================================================
echo   TamilVoice Kirana AI is now running!
echo ========================================================================
echo.
echo   Frontend App:   http://127.0.0.1:3000
echo   FastAPI Root:   http://127.0.0.1:8000
echo   API Endpoints:  http://127.0.0.1:8000/api
echo   Interactive Docs: http://127.0.0.1:8000/docs
echo   Health Status:  http://127.0.0.1:8000/health
echo.
echo   Both backend and frontend servers are running in separate windows.
echo   To stop the application, close those two terminal windows.
echo ========================================================================
echo.
pause
