@echo off
REM LUCID DISTROLESS BUILD SCRIPT - PHASES 2-5 ONLY
REM Builds API Gateway, Session Pipeline, Blockchain Core, and Payment Systems
REM Assumes Phase 1 (Core Infrastructure) is already built

echo ========================================
echo LUCID DISTROLESS BUILD - PHASES 2-5
echo ========================================
echo.
echo This script builds:
echo   Phase 2: API Gateway ^& Core Services
echo   Phase 3: Session Pipeline  
echo   Phase 4: Blockchain Core
echo   Phase 5: Payment Systems ^& Integration
echo.
echo NOTE: Phase 1 (Core Infrastructure) is skipped
echo       Ensure server-tools, tunnel-tools, and tor-proxy are already built
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

REM Check if Phase 1 images exist (optional verification)
echo Checking for Phase 1 dependencies...
docker buildx imagetools inspect pickme/lucid:server-tools >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Phase 1 images may not be available
    echo Please ensure server-tools, tunnel-tools, and tor-proxy are built
    echo.
    set /p continue="Continue anyway? (y/N): "
    if /i not "%continue%"=="y" (
        echo Build cancelled
        pause
        exit /b 1
    )
) else (
    echo Phase 1 dependencies verified
)

echo.
echo Starting phases 2-5 build process...
echo.

REM Execute the build script
powershell -ExecutionPolicy Bypass -File "build-phases-2-5.ps1" -Verbose

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Build process failed
    echo Check the log files for details
    pause
    exit /b 1
)

echo.
echo Phases 2-5 build process completed successfully!
echo.

REM Execute verification script for phases 2-5
echo Starting image verification for phases 2-5...
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
echo PHASES 2-5 BUILD COMPLETED
echo ========================================
echo.
echo All phases 2-5 distroless images have been built and verified.
echo Images are now available in Docker Hub: pickme/lucid
echo.
echo Built services:
echo   Phase 2: api-server, api-gateway, authentication
echo   Phase 3: session-chunker, session-encryptor, merkle-builder, session-orchestrator
echo   Phase 4: blockchain-api, blockchain-governance, blockchain-ledger, blockchain-sessions-data, blockchain-vm
echo   Phase 5: tron-node-client, payment-governance, payment-distribution, usdt-trc20, payout-router-v0, payout-router-kyc, payment-analytics, openapi-server, openapi-gateway, rdp-server-manager, admin-ui
echo.
echo Next steps:
echo 1. Deploy to Raspberry Pi using the compose files
echo 2. Run: ssh pickme@192.168.0.75
echo 3. Execute deployment commands from the build guide
echo.
pause
