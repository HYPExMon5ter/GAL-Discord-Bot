@echo off
REM ============================================
REM PaddleOCR Environment Setup Helper
REM ============================================

echo Setting up environment variables for PaddleOCR...

REM Disable slow model source checks (saves 5-10 seconds per startup)
set DISABLE_MODEL_SOURCE_CHECK=True

REM Set UTF-8 encoding for proper console output
set PYTHONIOENCODING=utf-8

echo Environment variables set:
echo   DISABLE_MODEL_SOURCE_CHECK=%DISABLE_MODEL_SOURCE_CHECK%
echo   PYTHONIOENCODING=%PYTHONIOENCODING%
echo.

echo ============================================
echo Next steps:
echo 1. Create a Discord channel named 'bot-admin' (or change in config.yaml)
echo 2. Start the bot with: python bot.py
echo 3. Post a TFT screenshot to #tournament-standings
echo ============================================
echo.

pause
