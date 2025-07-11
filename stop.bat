@echo off
echo ==========================================
echo  Stopping Transcription Service
echo ==========================================
echo.

docker-compose down

if %errorlevel% neq 0 (
    echo ERROR: Failed to stop the service
    pause
    exit /b 1
)

echo.
echo ✓ Service stopped successfully
echo.
pause