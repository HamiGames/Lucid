# LUCID Centralized Dockerfiles Script
# Moves all Dockerfiles to a centralized dockerfiles/ directory
# Updates Dockerfiles to reference modules from their actual locations

param(
    [switch]$DryRun = $false,
    [switch]$Force = $false,
    [string]$BackupDir = "backup_dockerfiles_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
)

Write-Host "🚀 LUCID Centralized Dockerfiles Script" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
}

# Create backup directory if not dry run
if (-not $DryRun) {
    Write-Host "📦 Creating backup directory: $BackupDir" -ForegroundColor Blue
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

# Define all Dockerfiles to move and their new locations
$DockerfileMap = @{
    # Sessions components
    "sessions/recorder/Dockerfile.keystroke-monitor.distroless" = "dockerfiles/sessions/Dockerfile.keystroke-monitor.distroless"
    "sessions/recorder/Dockerfile.window-focus-monitor.distroless" = "dockerfiles/sessions/Dockerfile.window-focus-monitor.distroless"
    "sessions/recorder/Dockerfile.resource-monitor.distroless" = "dockerfiles/sessions/Dockerfile.resource-monitor.distroless"
    "sessions/recorder/Dockerfile.session-recorder" = "dockerfiles/sessions/Dockerfile.session-recorder"
    "sessions/core/Dockerfile.orchestrator" = "dockerfiles/sessions/Dockerfile.orchestrator"
    "sessions/core/Dockerfile.chunker" = "dockerfiles/sessions/Dockerfile.chunker"
    "sessions/core/Dockerfile.merkle_builder" = "dockerfiles/sessions/Dockerfile.merkle-builder"
    "sessions/encryption/Dockerfile.encryptor" = "dockerfiles/sessions/Dockerfile.encryptor"
    
    # RDP components
    "RDP/recorder/Dockerfile.rdp-host.distroless" = "dockerfiles/rdp/Dockerfile.rdp-host.distroless"
    "RDP/recorder/Dockerfile.clipboard-handler.distroless" = "dockerfiles/rdp/Dockerfile.clipboard-handler.distroless"
    "RDP/recorder/Dockerfile.file-transfer-handler.distroless" = "dockerfiles/rdp/Dockerfile.file-transfer-handler.distroless"
    "RDP/recorder/Dockerfile.wayland-integration.distroless" = "dockerfiles/rdp/Dockerfile.wayland-integration.distroless"
    "RDP/server/Dockerfile.server-manager" = "dockerfiles/rdp/Dockerfile.server-manager"
    "RDP/server/Dockerfile.server-manager.simple" = "dockerfiles/rdp/Dockerfile.server-manager.simple"
    "RDP/server/Dockerfile.xrdp-integration" = "dockerfiles/rdp/Dockerfile.xrdp-integration"
    
    # Wallet components
    "wallet/walletd/Dockerfile.software-vault.distroless" = "dockerfiles/wallet/Dockerfile.software-vault.distroless"
    "wallet/walletd/Dockerfile.role-manager.distroless" = "dockerfiles/wallet/Dockerfile.role-manager.distroless"
    "wallet/walletd/Dockerfile.key-rotation.distroless" = "dockerfiles/wallet/Dockerfile.key-rotation.distroless"
    
    # Blockchain components
    "blockchain/chain-client/Dockerfile.on-system-chain-client.distroless" = "dockerfiles/blockchain/Dockerfile.on-system-chain-client.distroless"
    "blockchain/chain-client/Dockerfile.lucid-anchors-client.distroless" = "dockerfiles/blockchain/Dockerfile.lucid-anchors-client.distroless"
    "blockchain/tron_node/Dockerfile.tron-client" = "dockerfiles/blockchain/Dockerfile.tron-client"
    "blockchain/on_system_chain/Dockerfile.chain-client" = "dockerfiles/blockchain/Dockerfile.chain-client"
    "blockchain/api/Dockerfile" = "dockerfiles/blockchain/Dockerfile.api"
    "blockchain/api/Dockerfile.distroless" = "dockerfiles/blockchain/Dockerfile.api.distroless"
    "blockchain/deployment/Dockerfile.contract-deployment" = "dockerfiles/blockchain/Dockerfile.contract-deployment"
    "blockchain/deployment/Dockerfile.contract-deployment.simple" = "dockerfiles/blockchain/Dockerfile.contract-deployment.simple"
    
    # Admin components
    "admin/admin-ui/Dockerfile.admin-ui.distroless" = "dockerfiles/admin/Dockerfile.admin-ui.distroless"
    "admin/ui/Dockerfile.admin-ui" = "dockerfiles/admin/Dockerfile.admin-ui"
    
    # Node components
    "node/consensus/Dockerfile.leader-selection.distroless" = "dockerfiles/node/Dockerfile.leader-selection.distroless"
    "node/consensus/Dockerfile.task-proofs.distroless" = "dockerfiles/node/Dockerfile.task-proofs.distroless"
    "node/dht_crdt/Dockerfile.dht-node" = "dockerfiles/node/Dockerfile.dht-node"
    
    # Common components
    "common/governance/Dockerfile.lucid-governor.distroless" = "dockerfiles/common/Dockerfile.lucid-governor.distroless"
    "common/governance/Dockerfile.timelock.distroless" = "dockerfiles/common/Dockerfile.timelock.distroless"
    "common/server-tools/Dockerfile" = "dockerfiles/common/Dockerfile.server-tools"
    "common/server-tools/Dockerfile.distroless" = "dockerfiles/common/Dockerfile.server-tools.distroless"
    
    # Payment systems
    "payment-systems/tron-node/Dockerfile.payout-router-v0.distroless" = "dockerfiles/payment-systems/Dockerfile.payout-router-v0.distroless"
    "payment-systems/tron-node/Dockerfile.usdt-trc20.distroless" = "dockerfiles/payment-systems/Dockerfile.usdt-trc20.distroless"
    
    # Tools
    "tools/ops/ota/Dockerfile.update-manager.distroless" = "dockerfiles/tools/Dockerfile.update-manager.distroless"
    "tools/ops/ota/Dockerfile.signature-verifier.distroless" = "dockerfiles/tools/Dockerfile.signature-verifier.distroless"
}

# Function to update Dockerfile COPY commands to reference modules from their actual locations
function Update-DockerfilePaths {
    param(
        [string]$DockerfilePath,
        [string]$NewDockerfilePath
    )
    
    if (-not (Test-Path $DockerfilePath)) {
        Write-Host "⚠️  Dockerfile not found: $DockerfilePath" -ForegroundColor Yellow
        return
    }
    
    $content = Get-Content $DockerfilePath -Raw
    
    # Update COPY commands to reference modules from their actual locations
    # Sessions components
    if ($DockerfilePath -like "*sessions*") {
        $content = $content -replace "COPY sessions/recorder/ /app/sessions/recorder/", "COPY sessions/recorder/ /app/sessions/recorder/"
        $content = $content -replace "COPY sessions/ /app/sessions/", "COPY sessions/ /app/sessions/"
    }
    
    # RDP components
    if ($DockerfilePath -like "*rdp*") {
        $content = $content -replace "COPY RDP/recorder/ /app/RDP/recorder/", "COPY RDP/recorder/ /app/RDP/recorder/"
        $content = $content -replace "COPY RDP/ /app/RDP/", "COPY RDP/ /app/RDP/"
    }
    
    # Wallet components
    if ($DockerfilePath -like "*wallet*") {
        $content = $content -replace "COPY wallet/walletd/ /app/wallet/walletd/", "COPY wallet/walletd/ /app/wallet/walletd/"
        $content = $content -replace "COPY wallet/ /app/wallet/", "COPY wallet/ /app/wallet/"
    }
    
    # Blockchain components
    if ($DockerfilePath -like "*blockchain*") {
        $content = $content -replace "COPY blockchain/ /app/blockchain/", "COPY blockchain/ /app/blockchain/"
    }
    
    # Admin components
    if ($DockerfilePath -like "*admin*") {
        $content = $content -replace "COPY admin/ /app/admin/", "COPY admin/ /app/admin/"
    }
    
    # Node components
    if ($DockerfilePath -like "*node*") {
        $content = $content -replace "COPY node/ /app/node/", "COPY node/ /app/node/"
    }
    
    # Common components
    if ($DockerfilePath -like "*common*") {
        $content = $content -replace "COPY common/ /app/common/", "COPY common/ /app/common/"
    }
    
    # Payment systems
    if ($DockerfilePath -like "*payment*") {
        $content = $content -replace "COPY payment-systems/ /app/payment-systems/", "COPY payment-systems/ /app/payment-systems/"
    }
    
    # Tools
    if ($DockerfilePath -like "*tools*") {
        $content = $content -replace "COPY tools/ /app/tools/", "COPY tools/ /app/tools/"
    }
    
    if (-not $DryRun) {
        Set-Content -Path $NewDockerfilePath -Value $content -Encoding UTF8
        Write-Host "✅ Updated Dockerfile: $NewDockerfilePath" -ForegroundColor Green
    } else {
        Write-Host "🔍 Would update Dockerfile: $NewDockerfilePath" -ForegroundColor Cyan
    }
}

# Function to move Dockerfiles
function Move-Dockerfiles {
    foreach ($source in $DockerfileMap.Keys) {
        $destination = $DockerfileMap[$source]
        
        if (Test-Path $source) {
            if (-not $DryRun) {
                # Create backup
                Copy-Item $source "$BackupDir/$(Split-Path $source -Leaf)" -Force
                
                # Create destination directory
                $destDir = Split-Path $destination -Parent
                if (-not (Test-Path $destDir)) {
                    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
                }
                
                # Move the file
                Move-Item $source $destination -Force
                Write-Host "📦 Moved: $source -> $destination" -ForegroundColor Green
            } else {
                Write-Host "🔍 Would move: $source -> $destination" -ForegroundColor Cyan
            }
            
            # Update the Dockerfile paths
            Update-DockerfilePaths -DockerfilePath $source -NewDockerfilePath $destination
        } else {
            Write-Host "⚠️  Source not found: $source" -ForegroundColor Yellow
        }
    }
}

# Main execution
Write-Host "🔄 Starting centralized Dockerfiles reorganization..." -ForegroundColor Blue

# Step 1: Move Dockerfiles
Write-Host "`n📦 Step 1: Moving Dockerfiles to centralized dockerfiles/ directory" -ForegroundColor Blue
Move-Dockerfiles

Write-Host "`n🎉 Centralized Dockerfiles reorganization complete!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green

if (-not $DryRun) {
    Write-Host "📦 Backup created in: $BackupDir" -ForegroundColor Blue
    Write-Host "🚀 All Dockerfiles are now centralized in dockerfiles/ directory" -ForegroundColor Blue
    Write-Host "📁 Modules remain in their original locations and are referenced by COPY commands" -ForegroundColor Blue
} else {
    Write-Host "🔍 This was a dry run - no changes were made" -ForegroundColor Yellow
    Write-Host "🚀 Run with -Force to execute the centralization" -ForegroundColor Blue
}
