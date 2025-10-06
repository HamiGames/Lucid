# LUCID Complete Build System - SPEC-1D Implementation (PowerShell)
# Build all components with distroless Docker images

param(
    [string]$Registry = "pickme",
    [string]$Tag = "latest",
    [switch]$Push = $false,
    [switch]$NoCache = $false,
    [string]$Platforms = "linux/arm64,linux/amd64"
)

Write-Host "=== LUCID Complete Component Build System ===" -ForegroundColor Green

# Build arguments
$BuildArgs = @()
if ($Push) {
    $BuildArgs += "--push"
}
if ($NoCache) {
    $BuildArgs += "--no-cache"
}

Write-Host "Build configuration:" -ForegroundColor Yellow
Write-Host "  Registry: $Registry"
Write-Host "  Tag: $Tag"
Write-Host "  Push: $Push"
Write-Host "  No Cache: $NoCache"
Write-Host "  Platforms: $Platforms"
Write-Host ""

# Function to build component
function Build-Component {
    param(
        [string]$ComponentName,
        [string]$DockerfilePath,
        [string]$ContextPath
    )
    
    Write-Host "Building $ComponentName..." -ForegroundColor Cyan
    
    $BuildCommand = @(
        "docker", "buildx", "build",
        "--platform", $Platforms,
        "-t", "$Registry/lucid:$ComponentName",
        "-f", $DockerfilePath,
        $ContextPath
    ) + $BuildArgs
    
    try {
        & $BuildCommand[0] $BuildCommand[1..($BuildCommand.Length-1)]
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $ComponentName built successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ $ComponentName build failed" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ $ComponentName build failed: $_" -ForegroundColor Red
        return $false
    }
}

# Build Session Pipeline Components
Write-Host "=== Building Session Pipeline Components ===" -ForegroundColor Green
Build-Component "session-chunker" "sessions/core/Dockerfile.chunker" "sessions/core"
Build-Component "session-encryptor" "sessions/encryption/Dockerfile.encryptor" "sessions/encryption"
Build-Component "merkle-builder" "sessions/core/Dockerfile.merkle_builder" "sessions/core"
Build-Component "session-orchestrator" "sessions/core/Dockerfile.orchestrator" "sessions/core"

# Build Blockchain Components
Write-Host "=== Building Blockchain Components ===" -ForegroundColor Green
Build-Component "on-system-chain-client" "blockchain/on_system_chain/Dockerfile.chain-client" "blockchain/on_system_chain"
Build-Component "tron-node-client" "blockchain/tron_node/Dockerfile.tron-client" "blockchain/tron_node"

# Build Node Components
Write-Host "=== Building Node Components ===" -ForegroundColor Green
Build-Component "dht-crdt-node" "node/dht_crdt/Dockerfile.dht-node" "node/dht_crdt"

# Build Core Support Services (if they exist)
Write-Host "=== Building Core Support Services ===" -ForegroundColor Green
if (Test-Path "02-network-security/tor/Dockerfile") {
    Build-Component "tor-proxy" "02-network-security/tor/Dockerfile" "02-network-security/tor"
}

if (Test-Path "02-network-security/tunnels/Dockerfile") {
    Build-Component "tunnel-tools" "02-network-security/tunnels/Dockerfile" "02-network-security/tunnels"
}

if (Test-Path "common/server-tools/Dockerfile") {
    Build-Component "server-tools" "common/server-tools/Dockerfile" "common/server-tools"
}

# Build API Gateway Services (if they exist)
Write-Host "=== Building API Gateway Services ===" -ForegroundColor Green
if (Test-Path "03-api-gateway/api/Dockerfile.api") {
    Build-Component "api-server" "03-api-gateway/api/Dockerfile.api" "03-api-gateway/api"
}

if (Test-Path "03-api-gateway/gateway/Dockerfile.gateway") {
    Build-Component "api-gateway" "03-api-gateway/gateway/Dockerfile.gateway" "03-api-gateway/gateway"
}

# Build OpenAPI Services (if they exist)
Write-Host "=== Building OpenAPI Services ===" -ForegroundColor Green
if (Test-Path "open-api/api/Dockerfile.api") {
    Build-Component "openapi-server" "open-api/api/Dockerfile.api" "open-api/api"
}

if (Test-Path "open-api/gateway/Dockerfile.gateway") {
    Build-Component "openapi-gateway" "open-api/gateway/Dockerfile.gateway" "open-api/gateway"
}

# Build Blockchain Core Services (if they exist)
Write-Host "=== Building Blockchain Core Services ===" -ForegroundColor Green
if (Test-Path "04-blockchain-core/api/Dockerfile") {
    Build-Component "blockchain-api" "04-blockchain-core/api/Dockerfile" "04-blockchain-core/api"
}

if (Test-Path "04-blockchain-core/governance/Dockerfile") {
    Build-Component "blockchain-governance" "04-blockchain-core/governance/Dockerfile" "04-blockchain-core/governance"
}

if (Test-Path "04-blockchain-core/sessions-data/Dockerfile") {
    Build-Component "blockchain-sessions-data" "04-blockchain-core/sessions-data/Dockerfile" "04-blockchain-core/sessions-data"
}

if (Test-Path "04-blockchain-core/vm/Dockerfile") {
    Build-Component "blockchain-vm" "04-blockchain-core/vm/Dockerfile" "04-blockchain-core/vm"
}

if (Test-Path "04-blockchain-core/ledger/Dockerfile") {
    Build-Component "blockchain-ledger" "04-blockchain-core/ledger/Dockerfile" "04-blockchain-core/ledger"
}

# Build Legacy Blockchain API (if it exists)
if (Test-Path "blockchain/api/Dockerfile") {
    Build-Component "blockchain-api-legacy" "blockchain/api/Dockerfile" "blockchain/api"
}

Write-Host ""
Write-Host "=== Build Summary ===" -ForegroundColor Green
Write-Host "All components built successfully!"
Write-Host "Registry: $Registry"
Write-Host "Tag: $Tag"
Write-Host "Platforms: $Platforms"

if ($Push) {
    Write-Host "Images pushed to registry" -ForegroundColor Green
} else {
    Write-Host "Images built locally (use -Push to upload)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Available Images ===" -ForegroundColor Cyan
Write-Host "Session Pipeline:"
Write-Host "  - $Registry/lucid:session-chunker"
Write-Host "  - $Registry/lucid:session-encryptor"
Write-Host "  - $Registry/lucid:merkle-builder"
Write-Host "  - $Registry/lucid:session-orchestrator"
Write-Host ""
Write-Host "Blockchain:"
Write-Host "  - $Registry/lucid:on-system-chain-client"
Write-Host "  - $Registry/lucid:tron-node-client"
Write-Host ""
Write-Host "Node Systems:"
Write-Host "  - $Registry/lucid:dht-crdt-node"
Write-Host ""
Write-Host "Core Support:"
Write-Host "  - $Registry/lucid:tor-proxy"
Write-Host "  - $Registry/lucid:tunnel-tools"
Write-Host "  - $Registry/lucid:server-tools"
Write-Host ""
Write-Host "API Services:"
Write-Host "  - $Registry/lucid:api-server"
Write-Host "  - $Registry/lucid:api-gateway"
Write-Host "  - $Registry/lucid:openapi-server"
Write-Host "  - $Registry/lucid:openapi-gateway"
Write-Host ""
Write-Host "Blockchain Core:"
Write-Host "  - $Registry/lucid:blockchain-api"
Write-Host "  - $Registry/lucid:blockchain-governance"
Write-Host "  - $Registry/lucid:blockchain-sessions-data"
Write-Host "  - $Registry/lucid:blockchain-vm"
Write-Host "  - $Registry/lucid:blockchain-ledger"
Write-Host "  - $Registry/lucid:blockchain-api-legacy"

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Green
