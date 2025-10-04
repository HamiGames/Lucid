#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build Lucid DevContainer for local AMD64 development
    
.DESCRIPTION
    This script builds the devcontainer targeting AMD64 only to avoid ARM64 build issues.
    Use this for local Windows/Intel development when the Pi system is not available.
#>

param(
    [switch]$Clean = $false,
    [switch]$NoBuild = $false
)

# Color output functions
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }

Write-Info "Lucid RDP Local AMD64 DevContainer Builder"
Write-Info "=========================================="

if ($Clean) {
    Write-Info "Cleaning Docker system..."
    docker system prune -af
    docker builder prune -af
    docker network prune -f
    Write-Success "Docker system cleaned"
}

# Check Docker
try {
    docker info > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker is running"
    } else {
        Write-Error "Docker is not running"
        exit 1
    }
} catch {
    Write-Error "Docker not found"
    exit 1
}

# Ensure network exists
Write-Info "Ensuring Docker network exists..."
$networkCheck = docker network inspect lucid-dev_lucid_net 2>$null
if ($LASTEXITCODE -ne 0) {
    docker network create --driver bridge --attachable lucid-dev_lucid_net
    Write-Success "Created network: lucid-dev_lucid_net"
} else {
    Write-Success "Network exists: lucid-dev_lucid_net"
}

if ($NoBuild) {
    Write-Info "Skipping build (NoBuild flag specified)"
    exit 0
}

# Set build variables
$imageName = "pickme/lucid"
$version = "0.1.0"
$gitSha = (git rev-parse --short HEAD 2>$null) ?? "unknown"
$buildDate = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ" -AsUTC)

Write-Info "Building AMD64-only devcontainer..."
Write-Info "Image: $imageName`:$version"
Write-Info "Git SHA: $gitSha"
Write-Info "Build Date: $buildDate"

# Create temporary Dockerfile for AMD64 build
$tempDockerfile = ".devcontainer/Dockerfile.amd64"
$originalDockerfile = ".devcontainer/Dockerfile"

# Copy original dockerfile and modify for AMD64
Copy-Item $originalDockerfile $tempDockerfile

# Modify the MongoDB tools installation to skip ARM64 issues
$dockerfileContent = Get-Content $tempDockerfile -Raw
$dockerfileContent = $dockerfileContent -replace 'mongodb-database-tools', 'mongodb-mongosh'
$dockerfileContent | Set-Content $tempDockerfile

Write-Info "Building Docker image..."
try {
    $buildCommand = @(
        "docker", "build"
        "--platform", "linux/amd64"
        "--file", $tempDockerfile
        "--tag", "$imageName`:$version"
        "--tag", "$imageName`:dev-latest"
        "--tag", "$imageName`:$version-$gitSha"
        "--build-arg", "VERSION=$version"
        "--build-arg", "GIT_SHA=$gitSha"  
        "--build-arg", "BUILD_DATE=$buildDate"
        "."
    )
    
    Write-Info "Build command: $($buildCommand -join ' ')"
    
    & $buildCommand[0] $buildCommand[1..$buildCommand.Length]
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "DevContainer built successfully!"
        Write-Info "Available tags:"
        Write-Info "• $imageName`:$version"
        Write-Info "• $imageName`:dev-latest"
        Write-Info "• $imageName`:$version-$gitSha"
    } else {
        Write-Error "Docker build failed"
        exit 1
    }
} catch {
    Write-Error "Build command failed: $_"
    exit 1
} finally {
    # Clean up temporary dockerfile
    if (Test-Path $tempDockerfile) {
        Remove-Item $tempDockerfile
        Write-Info "Cleaned up temporary dockerfile"
    }
}

# Test the image
Write-Info "Testing built image..."
try {
    $testResult = docker run --rm --platform linux/amd64 "$imageName`:$version" python --version
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Image test passed: $testResult"
    } else {
        Write-Warning "Image test had issues but build completed"
    }
} catch {
    Write-Warning "Could not test image, but build completed"
}

Write-Success "Local AMD64 DevContainer build complete!"
Write-Info "You can now run: .\launch-devcontainer-vscode.ps1"