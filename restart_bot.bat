@echo off
REM ============================================
REM Clear Cache and Restart Bot - Helper Script
REM ============================================

echo.
echo ============================================
echo  Clearing Python Cache...
echo ============================================

REM Clear cache directories
if exist __pycache__ rmdir /s /q __pycache__
if exist core\events\handlers\__pycache__ rmdir /s /q core\events\handlers\__pycache__
if exist integrations\__pycache__ rmdir /s /q integrations\__pycache__

echo Cache cleared.
echo.

echo ============================================
echo  Clearing Database (Optional)...
echo ============================================
set /p clear_db="Clear recent submissions? (Y/N): "
if /i "%clear_db%"=="Y" (
    python clear_recent_submissions.py
)

echo.
echo ============================================
echo  Starting Bot...
echo ============================================

REM Set environment variables
set DISABLE_MODEL_SOURCE_CHECK=True
set PYTHONIOENCODING=utf-8

REM Start bot
python bot.py

pause
