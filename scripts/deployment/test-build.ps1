# Simple Docker Build Test Script for Lucid DevContainer
# Tests Docker functionality without complex multi-platform builds

param(
    [switch]$TestOnly,
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\test-build.ps1 [-TestOnly] [-Help]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -TestOnly   Only test local build, don't push"
    Write-Host "  -Help       Show this help"
    exit 0
}

$IMAGE_NAME = "pickme/lucid"
$DOCKERFILE_PATH = ".devcontainer/Dockerfile"

Write-Host "===== Simple Docker Build Test =====" -ForegroundColor Cyan
Write-Host "Image: $IMAGE_NAME" -ForegroundColor Yellow
Write-Host "Dockerfile: $DOCKERFILE_PATH" -ForegroundColor Yellow

# Step 1: Test Docker
Write-Host "Testing Docker daemon..." -ForegroundColor Yellow
try {
    docker info *>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[+] Docker is running" -ForegroundColor Green
    } else {
        Write-Host "[-] Docker not ready" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[-] Docker not accessible" -ForegroundColor Red
    exit 1
}

# Step 2: Test base image pull
Write-Host "Testing base image pull..." -ForegroundColor Yellow
try {
    Write-Host "Pulling python:3.12-slim..." -ForegroundColor Yellow
    $result = docker pull python:3.12-slim 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[+] Successfully pulled Python base image" -ForegroundColor Green
    } else {
        Write-Host "[-] Failed to pull Python base image" -ForegroundColor Red
        Write-Host "Error: $result" -ForegroundColor Red
        Write-Host ""
        Write-Host "This indicates DNS issues. Please run: .\fix-docker-dns.ps1" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "[-] Base image pull failed" -ForegroundColor Red
    exit 1
}

# Step 3: Test local build
Write-Host "Testing local build..." -ForegroundColor Yellow
try {
    # Build for current platform only
    $buildArgs = @(
        "--file", $DOCKERFILE_PATH,
        "--tag", "${IMAGE_NAME}:test-local",
        "."
    )
    
    Write-Host "Building image locally..." -ForegroundColor Yellow
    $buildResult = docker build @buildArgs 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[+] Local build successful" -ForegroundColor Green
    } else {
        Write-Host "[-] Local build failed" -ForegroundColor Red
        Write-Host "Build output:" -ForegroundColor Red
        Write-Host $buildResult -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[-] Build command failed" -ForegroundColor Red
    exit 1
}

# Step 4: Test container startup
Write-Host "Testing container startup..." -ForegroundColor Yellow
try {
    $containerId = docker run -d "$IMAGE_NAME:test-local" sleep 10
    Start-Sleep -Seconds 2
    
    $running = docker ps | Select-String $containerId
    if ($running) {
        Write-Host "[+] Container started successfully" -ForegroundColor Green
        docker stop $containerId *>$null
        docker rm $containerId *>$null
    } else {
        Write-Host "[-] Container failed to start" -ForegroundColor Red
        docker logs $containerId
        docker rm $containerId *>$null
        exit 1
    }
} catch {
    Write-Host "[-] Container test failed" -ForegroundColor Red
    exit 1
}

# Step 5: Cleanup
try {
    docker rmi "$IMAGE_NAME:test-local" *>$null
    Write-Host "[+] Cleaned up test image" -ForegroundColor Green
} catch {
    # Ignore cleanup errors
}

# Success
Write-Host ""
Write-Host "===== ALL TESTS PASSED =====" -ForegroundColor Green
Write-Host "[+] Docker daemon working" -ForegroundColor Green
Write-Host "[+] Base image pull working" -ForegroundColor Green  
Write-Host "[+] Local build working" -ForegroundColor Green
Write-Host "[+] Container startup working" -ForegroundColor Green

Write-Host ""
Write-Host "Docker build system is working correctly!" -ForegroundColor Cyan
Write-Host "You can now try: .\build-devcontainer.ps1 -TestOnly" -ForegroundColor Yellow

if (-not $TestOnly) {
    Write-Host ""
    Write-Host "Note: This was a simple test. For full multi-platform build:" -ForegroundColor Yellow
    Write-Host "Run: .\build-devcontainer.ps1" -ForegroundColor Yellow
}