@echo off
echo ==========================================
echo  Audio Transcription Service Installer
echo ==========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/
    echo After installation, restart this script.
    pause
    exit /b 1
)

echo ✓ Docker is installed

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker Compose is not available
    echo Please make sure Docker Desktop is running
    pause
    exit /b 1
)

echo ✓ Docker Compose is available

REM Check if .env file exists
if not exist .env (
    echo.
    echo ERROR: .env file not found!
    echo Please create a .env file with your OpenAI API key
    echo Example content:
    echo OPENAI_API_KEY=your_api_key_here
    echo.
    echo You can get your API key from: https://platform.openai.com/account/api-keys
    pause
    exit /b 1
)

echo ✓ .env file found

REM Create required directories
if not exist uploads mkdir uploads
if not exist temp_files mkdir temp_files
if not exist templates mkdir templates

echo ✓ Required directories created

echo.
echo Building and starting the transcription service...
echo This may take a few minutes for the first time...
echo.

REM Build and start the service
docker-compose up --build -d

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start the service
    echo Please check the error messages above
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  🎉 Installation Complete!
echo ==========================================
echo.
echo The transcription service is now running!
echo.
echo 📱 Access the web interface at: http://localhost:5000
echo.
echo 🔧 To stop the service: run 'stop.bat'
echo 🔧 To restart the service: run 'restart.bat'
echo 🔧 To view logs: run 'logs.bat'
echo.
echo Opening web browser...
timeout /t 3 /nobreak >nul
start http://localhost:5000
echo.
echo Press any key to exit...
pause >nul