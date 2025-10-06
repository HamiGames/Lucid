# LUCID Layer 2 Complete Build and Push Script
# Verifies Dockerfiles, builds all Layer 2 distroless images, and pushes to Docker Hub
# Multi-platform build for ARM64 Pi and AMD64 development

param(
    [string]$Registry = "pickme",
    [string]$Repository = "lucid",
    [string]$Tag = "latest",
    [switch]$Push = $true,
    [switch]$NoCache = $true,
    [switch]$Verbose = $false,
    [switch]$SkipVerification = $false
)

# Set error handling
$ErrorActionPreference = "Stop"

Write-Host "=== LUCID Layer 2 Complete Build and Push ===" -ForegroundColor Green
Write-Host "Registry: $Registry" -ForegroundColor Yellow
Write-Host "Repository: $Repository" -ForegroundColor Yellow
Write-Host "Tag: $Tag" -ForegroundColor Yellow
Write-Host "Push: $Push" -ForegroundColor Yellow
Write-Host "No Cache: $NoCache" -ForegroundColor Yellow
Write-Host "Verbose: $Verbose" -ForegroundColor Yellow
Write-Host "Skip Verification: $SkipVerification" -ForegroundColor Yellow
Write-Host ""

# Step 1: Verify Dockerfiles
if (-not $SkipVerification) {
    Write-Host "Step 1: Verifying Dockerfiles..." -ForegroundColor Cyan
    try {
        powershell -ExecutionPolicy Bypass -File scripts/verify-dockerfiles.ps1 -Verbose:$Verbose
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Dockerfile verification failed" -ForegroundColor Red
            exit 1
        }
        Write-Host "✅ All Dockerfiles verified successfully" -ForegroundColor Green
    } catch {
        Write-Host "❌ Dockerfile verification error: $_" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# Step 2: Verify Docker buildx
Write-Host "Step 2: Verifying Docker buildx..." -ForegroundColor Cyan
try {
    docker buildx version
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker buildx not available" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Docker buildx available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker buildx error: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Verify Docker Hub login
if ($Push) {
    Write-Host "Step 3: Verifying Docker Hub login..." -ForegroundColor Cyan
    try {
        $LoginInfo = docker info | Select-String "Username"
        if ($LoginInfo) {
            Write-Host "✅ Docker Hub login verified: $($LoginInfo.Line)" -ForegroundColor Green
        } else {
            Write-Host "❌ Docker Hub login required" -ForegroundColor Red
            Write-Host "Please run: docker login" -ForegroundColor Yellow
            exit 1
        }
    } catch {
        Write-Host "❌ Docker Hub login error: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Step 4: Build and push images
Write-Host "Step 4: Building and pushing Layer 2 distroless images..." -ForegroundColor Cyan

# Build configuration
$BuildArgs = @(
    "buildx", "build"
    "--platform", "linux/amd64,linux/arm64"
    "--no-cache"
    "--push"
    "--tag", "${Registry}/${Repository}:rdp-server-manager-${Tag}"
    "--tag", "${Registry}/${Repository}:rdp-server-manager"
    "--file", "RDP/server/Dockerfile.server-manager"
    "."
)

if ($Verbose) {
    $BuildArgs += "--progress=plain"
}

# Build RDP Server Manager
Write-Host "Building RDP Server Manager..." -ForegroundColor Cyan
try {
    if ($Verbose) {
        Write-Host "Command: docker $($BuildArgs -join ' ')" -ForegroundColor Gray
    }
    
    docker @BuildArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ RDP Server Manager built and pushed successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ RDP Server Manager build failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ RDP Server Manager build error: $_" -ForegroundColor Red
    exit 1
}

# Build xrdp Integration
Write-Host "Building xrdp Integration..." -ForegroundColor Cyan
$BuildArgs[6] = "${Registry}/${Repository}:xrdp-integration-${Tag}"
$BuildArgs[7] = "${Registry}/${Repository}:xrdp-integration"
$BuildArgs[9] = "RDP/server/Dockerfile.xrdp-integration"

try {
    if ($Verbose) {
        Write-Host "Command: docker $($BuildArgs -join ' ')" -ForegroundColor Gray
    }
    
    docker @BuildArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ xrdp Integration built and pushed successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ xrdp Integration build failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ xrdp Integration build error: $_" -ForegroundColor Red
    exit 1
}

# Build Contract Deployment
Write-Host "Building Contract Deployment..." -ForegroundColor Cyan
$BuildArgs[6] = "${Registry}/${Repository}:contract-deployment-${Tag}"
$BuildArgs[7] = "${Registry}/${Repository}:contract-deployment"
$BuildArgs[9] = "blockchain/deployment/Dockerfile.contract-deployment"

try {
    if ($Verbose) {
        Write-Host "Command: docker $($BuildArgs -join ' ')" -ForegroundColor Gray
    }
    
    docker @BuildArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Contract Deployment built and pushed successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Contract Deployment build failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Contract Deployment build error: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Layer 2 Distroless Build Complete ===" -ForegroundColor Green
Write-Host "Built and pushed images:" -ForegroundColor Yellow
Write-Host "  - ${Registry}/${Repository}:rdp-server-manager" -ForegroundColor White
Write-Host "  - ${Registry}/${Repository}:xrdp-integration" -ForegroundColor White
Write-Host "  - ${Registry}/${Repository}:contract-deployment" -ForegroundColor White

Write-Host ""
Write-Host "All images pushed to Docker Hub registry" -ForegroundColor Green
Write-Host "Images are ready for deployment on Pi 5" -ForegroundColor Green

# Step 5: Verify pushed images
if ($Push) {
    Write-Host ""
    Write-Host "Step 5: Verifying pushed images..." -ForegroundColor Cyan
    
    $Images = @(
        "${Registry}/${Repository}:rdp-server-manager",
        "${Registry}/${Repository}:xrdp-integration",
        "${Registry}/${Repository}:contract-deployment"
    )
    
    foreach ($Image in $Images) {
        try {
            Write-Host "Verifying $Image..." -ForegroundColor Gray
            docker manifest inspect $Image | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ $Image verified" -ForegroundColor Green
            } else {
                Write-Host "❌ $Image verification failed" -ForegroundColor Red
            }
        } catch {
            Write-Host "❌ $Image verification error: $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "=== Build Process Complete ===" -ForegroundColor Green
Write-Host "Layer 2 distroless images are ready for deployment" -ForegroundColor Green
