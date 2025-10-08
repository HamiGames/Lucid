# Timelock Governance Deployment Script for Windows
# This script deploys the timelock governance service on Windows

param(
    [string]$MongoUri = "mongodb://lucid:lucid@127.0.0.1:27019/lucid?authSource=admin",
    [string]$OutputDir = "C:\data\timelock",
    [string]$ConfigFile = "",
    [switch]$Build = $false,
    [switch]$Test = $false,
    [switch]$Help = $false
)

if ($Help) {
    Write-Host "Timelock Governance Deployment Script" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\deploy_timelock.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -MongoUri     MongoDB connection URI (default: mongodb://lucid:lucid@127.0.0.1:27019/lucid?authSource=admin)"
    Write-Host "  -OutputDir    Output directory for timelock data (default: C:\data\timelock)"
    Write-Host "  -ConfigFile   Path to configuration file (optional)"
    Write-Host "  -Build        Build Docker image before deployment"
    Write-Host "  -Test         Run tests after deployment"
    Write-Host "  -Help         Show this help message"
    Write-Host ""
    exit 0
}

Write-Host "Starting Timelock Governance Deployment..." -ForegroundColor Green

# Set error action preference
$ErrorActionPreference = "Stop"

try {
    # Create output directory
    if (-not (Test-Path $OutputDir)) {
        Write-Host "Creating output directory: $OutputDir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    }

    # Install Python dependencies if needed
    Write-Host "Checking Python dependencies..." -ForegroundColor Yellow
    $requirementsFile = "requirements.timelock.txt"
    if (Test-Path $requirementsFile) {
        Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
        pip install -r $requirementsFile
    }

    # Build Docker image if requested
    if ($Build) {
        Write-Host "Building Docker image..." -ForegroundColor Yellow
        docker build -f Dockerfile.timelock -t lucid-timelock:latest .
        
        if ($LASTEXITCODE -ne 0) {
            throw "Docker build failed"
        }
        
        Write-Host "Docker image built successfully" -ForegroundColor Green
    }

    # Set environment variables
    $env:MONGO_URI = $MongoUri
    $env:LUCID_TIMELOCK_OUTPUT_DIR = $OutputDir
    
    if ($ConfigFile -and (Test-Path $ConfigFile)) {
        $env:LUCID_TIMELOCK_CONFIG_FILE = $ConfigFile
    }

    # Run tests if requested
    if ($Test) {
        Write-Host "Running timelock tests..." -ForegroundColor Yellow
        python test_timelock.py
        
        if ($LASTEXITCODE -ne 0) {
            throw "Tests failed"
        }
        
        Write-Host "All tests passed!" -ForegroundColor Green
    }

    # Start timelock service
    Write-Host "Starting timelock governance service..." -ForegroundColor Yellow
    
    $startArgs = @(
        "start_timelock.py"
    )
    
    if ($ConfigFile) {
        $startArgs += "--config", $ConfigFile
    }
    
    $startArgs += "--output-dir", $OutputDir
    $startArgs += "--mongo-uri", $MongoUri
    
    python @startArgs

    Write-Host "Timelock governance service started successfully!" -ForegroundColor Green

} catch {
    Write-Host "Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "Timelock Governance Deployment Complete!" -ForegroundColor Green
