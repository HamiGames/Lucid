# LUCID Layer 2 Build Script - Distroless Images
# Builds all Layer 2 Service Integration components with distroless security
# Multi-platform build for ARM64 Pi and AMD64 development

param(
    [string]$Registry = "pickme",
    [string]$Tag = "latest",
    [switch]$Push = $false,
    [switch]$NoCache = $false
)

# Set error handling
$ErrorActionPreference = "Stop"

# Build configuration
$BuildArgs = @(
    "--platform", "linux/amd64,linux/arm64"
    "--tag", "${Registry}/lucid:rdp-server-manager-${Tag}"
    "--tag", "${Registry}/lucid:rdp-server-manager"
    "--file", "RDP/server/Dockerfile.server-manager"
    "."
)

if ($NoCache) {
    $BuildArgs += "--no-cache"
}

if ($Push) {
    $BuildArgs += "--push"
}

Write-Host "=== LUCID Layer 2 Distroless Build ===" -ForegroundColor Green
Write-Host "Registry: $Registry" -ForegroundColor Yellow
Write-Host "Tag: $Tag" -ForegroundColor Yellow
Write-Host "Push: $Push" -ForegroundColor Yellow
Write-Host "No Cache: $NoCache" -ForegroundColor Yellow
Write-Host ""

# Build RDP Server Manager
Write-Host "Building RDP Server Manager..." -ForegroundColor Cyan
try {
    docker buildx build @BuildArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ RDP Server Manager built successfully" -ForegroundColor Green
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
$BuildArgs[3] = "${Registry}/lucid:xrdp-integration-${Tag}"
$BuildArgs[4] = "${Registry}/lucid:xrdp-integration"
$BuildArgs[6] = "RDP/server/Dockerfile.xrdp-integration"

try {
    docker buildx build @BuildArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ xrdp Integration built successfully" -ForegroundColor Green
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
$BuildArgs[3] = "${Registry}/lucid:contract-deployment-${Tag}"
$BuildArgs[4] = "${Registry}/lucid:contract-deployment"
$BuildArgs[6] = "blockchain/deployment/Dockerfile.contract-deployment"

try {
    docker buildx build @BuildArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Contract Deployment built successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Contract Deployment build failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Contract Deployment build error: $_" -ForegroundColor Red
    exit 1
    exit 1
}

Write-Host ""
Write-Host "=== Layer 2 Build Complete ===" -ForegroundColor Green
Write-Host "Built images:" -ForegroundColor Yellow
Write-Host "  - ${Registry}/lucid:rdp-server-manager" -ForegroundColor White
Write-Host "  - ${Registry}/lucid:xrdp-integration" -ForegroundColor White
Write-Host "  - ${Registry}/lucid:contract-deployment" -ForegroundColor White

if ($Push) {
    Write-Host ""
    Write-Host "All images pushed to registry" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "To push images, run with -Push flag" -ForegroundColor Yellow
}
