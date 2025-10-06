# LUCID Layer 2 Distroless Build and Push Script
# Builds all Layer 2 Service Integration components with distroless security
# Multi-platform build for ARM64 Pi and AMD64 development
# Pushes to Docker Hub registry

param(
    [string]$Registry = "pickme",
    [string]$Repository = "lucid",
    [string]$Tag = "latest",
    [switch]$Push = $true,
    [switch]$NoCache = $true,
    [switch]$Verbose = $false
)

# Set error handling
$ErrorActionPreference = "Stop"

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

Write-Host "=== LUCID Layer 2 Distroless Build and Push ===" -ForegroundColor Green
Write-Host "Registry: $Registry" -ForegroundColor Yellow
Write-Host "Repository: $Repository" -ForegroundColor Yellow
Write-Host "Tag: $Tag" -ForegroundColor Yellow
Write-Host "Push: $Push" -ForegroundColor Yellow
Write-Host "No Cache: $NoCache" -ForegroundColor Yellow
Write-Host "Verbose: $Verbose" -ForegroundColor Yellow
Write-Host ""

# Verify Docker buildx is available
Write-Host "Verifying Docker buildx..." -ForegroundColor Cyan
try {
    docker buildx version
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker buildx not available" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Docker buildx error: $_" -ForegroundColor Red
    exit 1
}

# Verify Docker Hub login
if ($Push) {
    Write-Host "Verifying Docker Hub login..." -ForegroundColor Cyan
    try {
        docker info | Select-String "Username"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Docker Hub login required" -ForegroundColor Red
            Write-Host "Please run: docker login" -ForegroundColor Yellow
            exit 1
        }
    } catch {
        Write-Host "❌ Docker Hub login error: $_" -ForegroundColor Red
        exit 1
    }
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

# Build Session Host Manager (if exists)
if (Test-Path "RDP/server/Dockerfile.session-host-manager") {
    Write-Host "Building Session Host Manager..." -ForegroundColor Cyan
    $BuildArgs[6] = "${Registry}/${Repository}:session-host-manager-${Tag}"
    $BuildArgs[7] = "${Registry}/${Repository}:session-host-manager"
    $BuildArgs[9] = "RDP/server/Dockerfile.session-host-manager"

    try {
        if ($Verbose) {
            Write-Host "Command: docker $($BuildArgs -join ' ')" -ForegroundColor Gray
        }
        
        docker @BuildArgs
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Session Host Manager built and pushed successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ Session Host Manager build failed" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "❌ Session Host Manager build error: $_" -ForegroundColor Red
        exit 1
    }
}

# Build Contract Compiler (if exists)
if (Test-Path "blockchain/deployment/Dockerfile.contract-compiler") {
    Write-Host "Building Contract Compiler..." -ForegroundColor Cyan
    $BuildArgs[6] = "${Registry}/${Repository}:contract-compiler-${Tag}"
    $BuildArgs[7] = "${Registry}/${Repository}:contract-compiler"
    $BuildArgs[9] = "blockchain/deployment/Dockerfile.contract-compiler"

    try {
        if ($Verbose) {
            Write-Host "Command: docker $($BuildArgs -join ' ')" -ForegroundColor Gray
        }
        
        docker @BuildArgs
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Contract Compiler built and pushed successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ Contract Compiler build failed" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "❌ Contract Compiler build error: $_" -ForegroundColor Red
        exit 1
    }
}

# Build Deployment Orchestrator (if exists)
if (Test-Path "blockchain/deployment/Dockerfile.deployment-orchestrator") {
    Write-Host "Building Deployment Orchestrator..." -ForegroundColor Cyan
    $BuildArgs[6] = "${Registry}/${Repository}:deployment-orchestrator-${Tag}"
    $BuildArgs[7] = "${Registry}/${Repository}:deployment-orchestrator"
    $BuildArgs[9] = "blockchain/deployment/Dockerfile.deployment-orchestrator"

    try {
        if ($Verbose) {
            Write-Host "Command: docker $($BuildArgs -join ' ')" -ForegroundColor Gray
        }
        
        docker @BuildArgs
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Deployment Orchestrator built and pushed successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ Deployment Orchestrator build failed" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "❌ Deployment Orchestrator build error: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "=== Layer 2 Distroless Build Complete ===" -ForegroundColor Green
Write-Host "Built and pushed images:" -ForegroundColor Yellow
Write-Host "  - ${Registry}/${Repository}:rdp-server-manager" -ForegroundColor White
Write-Host "  - ${Registry}/${Repository}:xrdp-integration" -ForegroundColor White
Write-Host "  - ${Registry}/${Repository}:contract-deployment" -ForegroundColor White

if (Test-Path "RDP/server/Dockerfile.session-host-manager") {
    Write-Host "  - ${Registry}/${Repository}:session-host-manager" -ForegroundColor White
}

if (Test-Path "blockchain/deployment/Dockerfile.contract-compiler") {
    Write-Host "  - ${Registry}/${Repository}:contract-compiler" -ForegroundColor White
}

if (Test-Path "blockchain/deployment/Dockerfile.deployment-orchestrator") {
    Write-Host "  - ${Registry}/${Repository}:deployment-orchestrator" -ForegroundColor White
}

Write-Host ""
Write-Host "All images pushed to Docker Hub registry" -ForegroundColor Green
Write-Host "Images are ready for deployment on Pi 5" -ForegroundColor Green
