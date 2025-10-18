@echo off
echo Guardian Angel League Dashboard Starting Up...
echo ==================================================

REM Start FastAPI backend in new window
echo Starting FastAPI backend...
start "Backend API" cmd /k "cd /d C:\Users\blake\PycharmProjects\New-GAL-Discord-Bot && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a moment for API to start
timeout /t 5 /nobreak >nul

REM Start Next.js frontend in new window
echo Starting Next.js frontend...
start "Frontend" cmd /k "cd dashboard && npm run dev"

echo.
echo Dashboard is starting up!
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Both services are running in separate windows.
echo Close those windows to stop the services.
pause
