# Lucid Distroless Images - Build and Push Script (PowerShell)
# Builds all distroless images and pushes to pickme/lucid Docker Hub repository
# Usage: .\build-and-push-distroless.ps1

$ErrorActionPreference = "Stop"

# Docker Hub repository
$DOCKER_REPO = "pickme/lucid"

# Build platforms (Pi ARM64 + AMD64)
$PLATFORMS = "linux/arm64,linux/amd64"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "Lucid Distroless Images Build & Push" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Ensure logged into Docker Hub
Write-Host "[INFO] Checking Docker Hub login..." -ForegroundColor Blue
$dockerInfo = docker info 2>&1 | Out-String
if ($dockerInfo -notmatch "Username") {
    Write-Host "[ERROR] Not logged into Docker Hub. Please run: docker login" -ForegroundColor Red
    exit 1
}

Write-Host "[✓] Docker Hub login confirmed" -ForegroundColor Green
Write-Host ""

# Function to build and push an image
function Build-And-Push {
    param(
        [string]$ServiceName,
        [string]$DockerfilePath,
        [string]$ContextPath
    )
    
    $tag = "${DOCKER_REPO}:${ServiceName}"
    
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host "Building: $ServiceName" -ForegroundColor Blue
    Write-Host "Dockerfile: $DockerfilePath" -ForegroundColor Blue
    Write-Host "Context: $ContextPath" -ForegroundColor Blue
    Write-Host "Tag: $tag" -ForegroundColor Blue
    Write-Host "========================================" -ForegroundColor Blue
    
    docker buildx build `
        --platform $PLATFORMS `
        -f $DockerfilePath `
        -t $tag `
        --push `
        $ContextPath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[✓] Successfully built and pushed: $tag" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "[✗] Failed to build: $ServiceName" -ForegroundColor Red
        throw "Build failed for $ServiceName"
    }
}

# =============================================================================
# Layer 1: Session Pipeline Services
# =============================================================================
Write-Host "=== Layer 1: Session Pipeline ===" -ForegroundColor Blue

Build-And-Push -ServiceName "session-chunker" `
    -DockerfilePath "sessions/core/Dockerfile.chunker" `
    -ContextPath "."

Build-And-Push -ServiceName "session-encryptor" `
    -DockerfilePath "sessions/encryption/Dockerfile.encryptor" `
    -ContextPath "."

Build-And-Push -ServiceName "merkle-builder" `
    -DockerfilePath "sessions/core/Dockerfile.merkle_builder" `
    -ContextPath "."

Build-And-Push -ServiceName "session-orchestrator" `
    -DockerfilePath "sessions/core/Dockerfile.orchestrator" `
    -ContextPath "."

# =============================================================================
# Layer 1: Authentication Service
# =============================================================================
Write-Host "=== Layer 1: Authentication ===" -ForegroundColor Blue

Build-And-Push -ServiceName "authentication" `
    -DockerfilePath "auth/Dockerfile.authentication" `
    -ContextPath "."

# =============================================================================
# Core Support Services
# =============================================================================
Write-Host "=== Core Support Services ===" -ForegroundColor Blue

Build-And-Push -ServiceName "server-tools" `
    -DockerfilePath "common/server-tools/Dockerfile" `
    -ContextPath "common/server-tools"

Build-And-Push -ServiceName "tunnel-tools" `
    -DockerfilePath "02-network-security/tunnels/Dockerfile" `
    -ContextPath "02-network-security/tunnels"

Build-And-Push -ServiceName "tor-proxy" `
    -DockerfilePath "02-network-security/tor/Dockerfile" `
    -ContextPath "02-network-security/tor"

# =============================================================================
# API Gateway Services (03-api-gateway)
# =============================================================================
Write-Host "=== API Gateway Services (Stage 0) ===" -ForegroundColor Blue

Build-And-Push -ServiceName "api-gateway" `
    -DockerfilePath "03-api-gateway/gateway/Dockerfile.gateway" `
    -ContextPath "03-api-gateway/gateway"

Build-And-Push -ServiceName "api-server" `
    -DockerfilePath "03-api-gateway/api/Dockerfile.api" `
    -ContextPath "03-api-gateway/api"

# =============================================================================
# Open API Services
# =============================================================================
Write-Host "=== Open API Services ===" -ForegroundColor Blue

Build-And-Push -ServiceName "openapi-gateway" `
    -DockerfilePath "open-api/gateway/Dockerfile.gateway" `
    -ContextPath "open-api/gateway"

Build-And-Push -ServiceName "openapi-server" `
    -DockerfilePath "open-api/api/Dockerfile.api" `
    -ContextPath "open-api/api"

# =============================================================================
# Blockchain Core Services
# =============================================================================
Write-Host "=== Blockchain Core Services ===" -ForegroundColor Blue

Build-And-Push -ServiceName "blockchain-api" `
    -DockerfilePath "04-blockchain-core/api/Dockerfile" `
    -ContextPath "04-blockchain-core/api"

Build-And-Push -ServiceName "blockchain-governance" `
    -DockerfilePath "04-blockchain-core/governance/Dockerfile" `
    -ContextPath "04-blockchain-core/governance"

Build-And-Push -ServiceName "blockchain-sessions-data" `
    -DockerfilePath "04-blockchain-core/sessions-data/Dockerfile" `
    -ContextPath "04-blockchain-core/sessions-data"

Build-And-Push -ServiceName "blockchain-vm" `
    -DockerfilePath "04-blockchain-core/vm/Dockerfile" `
    -ContextPath "04-blockchain-core/vm"

Build-And-Push -ServiceName "blockchain-ledger" `
    -DockerfilePath "04-blockchain-core/ledger/Dockerfile" `
    -ContextPath "04-blockchain-core/ledger"

# =============================================================================
# Legacy Blockchain API
# =============================================================================
Write-Host "=== Legacy Blockchain API ===" -ForegroundColor Blue

Build-And-Push -ServiceName "blockchain-api-legacy" `
    -DockerfilePath "blockchain/api/Dockerfile" `
    -ContextPath "blockchain/api"

# =============================================================================
# Summary
# =============================================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Build and Push Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "All images have been pushed to: $DOCKER_REPO" -ForegroundColor Green
Write-Host ""
Write-Host "Available images:" -ForegroundColor Blue
Write-Host "  - ${DOCKER_REPO}:session-chunker"
Write-Host "  - ${DOCKER_REPO}:session-encryptor"
Write-Host "  - ${DOCKER_REPO}:merkle-builder"
Write-Host "  - ${DOCKER_REPO}:session-orchestrator"
Write-Host "  - ${DOCKER_REPO}:authentication"
Write-Host "  - ${DOCKER_REPO}:server-tools"
Write-Host "  - ${DOCKER_REPO}:tunnel-tools"
Write-Host "  - ${DOCKER_REPO}:tor-proxy"
Write-Host "  - ${DOCKER_REPO}:api-gateway"
Write-Host "  - ${DOCKER_REPO}:api-server"
Write-Host "  - ${DOCKER_REPO}:openapi-gateway"
Write-Host "  - ${DOCKER_REPO}:openapi-server"
Write-Host "  - ${DOCKER_REPO}:blockchain-api"
Write-Host "  - ${DOCKER_REPO}:blockchain-governance"
Write-Host "  - ${DOCKER_REPO}:blockchain-sessions-data"
Write-Host "  - ${DOCKER_REPO}:blockchain-vm"
Write-Host "  - ${DOCKER_REPO}:blockchain-ledger"
Write-Host "  - ${DOCKER_REPO}:blockchain-api-legacy"
Write-Host ""
Write-Host "To pull an image on your Pi:" -ForegroundColor Blue
Write-Host "  docker pull ${DOCKER_REPO}:<image-name>"
Write-Host ""

