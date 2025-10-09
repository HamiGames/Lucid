@echo off
REM LUCID DISTROLESS BUILD AND DEPLOY BATCH SCRIPT
REM Executes the complete build and verification process

echo ========================================
echo LUCID DISTROLESS BUILD AND DEPLOY
echo ========================================
echo.

REM Check if PowerShell is available
powershell -Command "Get-Host" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: PowerShell is not available
    pause
    exit /b 1
)

REM Check if Docker is available
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not available
    pause
    exit /b 1
)

echo Pre-flight checks passed...
echo.

REM Execute the build script
echo Starting distroless image build process...
echo.
powershell -ExecutionPolicy Bypass -File "build-distroless-phases.ps1" -Verbose

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Build process failed
    echo Check the log files for details
    pause
    exit /b 1
)

echo.
echo Build process completed successfully!
echo.

REM Execute verification script
echo Starting image verification...
echo.
powershell -ExecutionPolicy Bypass -File "verify-distroless-images.ps1" -Verbose

if %errorlevel% neq 0 (
    echo.
    echo WARNING: Some images failed verification
    echo Check the verification log for details
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD AND VERIFICATION COMPLETED
echo ========================================
echo.
echo All distroless images have been built and verified.
echo Images are now available in Docker Hub: pickme/lucid
echo.
echo Next steps:
echo 1. Deploy to Raspberry Pi using the compose files
echo 2. Run: ssh pickme@192.168.0.75
echo 3. Execute deployment commands from the build guide
echo.
pause
