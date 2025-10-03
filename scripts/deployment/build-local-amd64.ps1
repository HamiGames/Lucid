#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build Lucid DevContainer for local AMD64 development
#>

param(
    [switch]$Clean = $false
)

function Write-Success { 
    param($Message) 
    Write-Host "[OK] $Message" -ForegroundColor Green 
}

function Write-Info { 
    param($Message) 
    Write-Host "[INFO] $Message" -ForegroundColor Cyan 
}

function Write-Warning { 
    param($Message) 
    Write-Host "[WARN] $Message" -ForegroundColor Yellow 
}

function Write-Error { 
    param($Message) 
    Write-Host "[ERROR] $Message" -ForegroundColor Red 
}

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

# Set build variables
$imageName = "pickme/lucid"
$version = "0.1.0"
$gitSha = (git rev-parse --short HEAD 2>$null)
if (-not $gitSha) { $gitSha = "unknown" }
$buildDate = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ" -AsUTC)

Write-Info "Building AMD64-only devcontainer..."
Write-Info "Image: ${imageName}:${version}"
Write-Info "Git SHA: $gitSha"
Write-Info "Build Date: $buildDate"

Write-Info "Building Docker image..."
docker build --platform linux/amd64 --file .devcontainer/Dockerfile --tag "${imageName}:${version}" --tag "${imageName}:dev-latest" --build-arg VERSION=$version --build-arg GIT_SHA=$gitSha --build-arg BUILD_DATE=$buildDate .

if ($LASTEXITCODE -eq 0) {
    Write-Success "DevContainer built successfully!"
    Write-Info "Available tags:"
    Write-Info "- ${imageName}:${version}"
    Write-Info "- ${imageName}:dev-latest"
} else {
    Write-Error "Docker build failed"
    exit 1
}

Write-Success "Local AMD64 DevContainer build complete!"
Write-Info "You can now run: .\launch-devcontainer-vscode.ps1"