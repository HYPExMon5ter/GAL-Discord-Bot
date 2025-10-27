@echo off
echo Starting API Server...
echo ==============================
echo.
echo API will be available at: http://localhost:8000
echo API Documentation at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

cd /d "C:\Users\blake\PycharmProjects\New-GAL-Discord-Bot"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

pause
