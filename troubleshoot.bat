@echo off
echo ==========================================
echo  Transcription Service Troubleshooter
echo ==========================================
echo.

echo Checking Docker installation...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed or not in PATH
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/
    echo.
    goto :end
) else (
    echo ✓ Docker is installed
)

echo.
echo Checking Docker Compose...
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not available
    echo Please make sure Docker Desktop is installed and running
    echo.
    goto :end
) else (
    echo ✓ Docker Compose is available
)

echo.
echo Checking if Docker Desktop is running...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Desktop is not running
    echo Please start Docker Desktop and wait for it to fully load
    echo Look for the Docker whale icon in your system tray
    echo When it shows "Docker Desktop is running", try again
    echo.
    goto :end
) else (
    echo ✓ Docker Desktop is running
)

echo.
echo Checking .env file...
if not exist .env (
    echo ❌ .env file not found
    echo Please create a .env file with your OpenAI API key
    echo Example content:
    echo OPENAI_API_KEY=your_api_key_here
    echo.
    goto :end
) else (
    echo ✓ .env file found
)

echo.
echo Checking required files...
if not exist Dockerfile (
    echo ❌ Dockerfile not found
    goto :end
) else (
    echo ✓ Dockerfile found
)

if not exist docker-compose.yml (
    echo ❌ docker-compose.yml not found
    goto :end
) else (
    echo ✓ docker-compose.yml found
)

if not exist app.py (
    echo ❌ app.py not found
    goto :end
) else (
    echo ✓ app.py found
)

if not exist requirements.txt (
    echo ❌ requirements.txt not found
    goto :end
) else (
    echo ✓ requirements.txt found
)

if not exist templates\index.html (
    echo ❌ templates\index.html not found
    goto :end
) else (
    echo ✓ templates\index.html found
)

echo.
echo Checking service status...
docker-compose ps 2>nul | find "transcription-service" >nul
if %errorlevel% neq 0 (
    echo ❌ Service is not running
    echo Try running install.bat to start the service
) else (
    echo ✓ Service appears to be running
    echo Try accessing: http://localhost:5000
)

echo.
echo ==========================================
echo  Troubleshooting Complete
echo ==========================================
echo.
echo If all checks pass but you still have issues:
echo 1. Try running: restart.bat
echo 2. Check logs with: logs.bat
echo 3. Make sure port 5000 is not used by another program
echo.

:end
pause