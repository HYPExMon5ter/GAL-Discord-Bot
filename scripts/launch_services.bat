@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo     Guardian Angel League Dashboard Launcher (Windows)
echo ========================================================
echo.

:: Check if we're in the right directory
if not exist "bot.py" (
    echo ERROR: Please run this script from the project root directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

:: Start FastAPI backend in new window
echo 🚀 Starting FastAPI backend...
start "GAL - Backend API" cmd /k "cd /d %CD% && echo Starting FastAPI on http://localhost:8000 && echo API Docs at http://localhost:8000/docs && echo. && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait a moment for API to start
echo ⏳ Waiting for API to initialize...
timeout /t 5 /nobreak >nul

:: Start Next.js frontend in new window
echo 🎨 Starting Next.js frontend...
start "GAL - Frontend Dashboard" cmd /k "cd /d %CD%\dashboard && echo Starting Dashboard on http://localhost:3000 && echo. && npm run dev"

:: Give services a moment to start
timeout /t 3 /nobreak >nul

echo.
echo ========================================================
echo 🎉 Dashboard is running!
echo ========================================================
echo 📊 Frontend:    http://localhost:3000
echo 🔧 Backend API: http://localhost:8000
echo 📚 API Docs:   http://localhost:8000/docs
echo ========================================================
echo 💡 Both services are running in separate windows
echo 💡 Close those windows or press Ctrl+C here to stop
echo ========================================================
echo.

:: Wait for user to close
pause

:: Optional: Attempt to close service windows
echo.
echo 🛑 Attempting to stop services...
taskkill /fi "WINDOWTITLE eq GAL - Backend API*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq GAL - Frontend Dashboard*" /f >nul 2>&1
echo ✅ Done
