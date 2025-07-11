@echo off
echo ==========================================
echo  Restarting Transcription Service
echo ==========================================
echo.

echo Stopping service...
docker-compose down

echo.
echo Starting service...
docker-compose up -d

if %errorlevel% neq 0 (
    echo ERROR: Failed to restart the service
    pause
    exit /b 1
)

echo.
echo ✓ Service restarted successfully
echo 📱 Access at: http://localhost:5000
echo.
pause