# LUCID Infrastructure Reorganization Script
# Reorganizes Dockerfiles into proper infrastructure directory structure

param(
    [switch]$DryRun = $false,
    [switch]$Force = $false,
    [string]$BackupDir = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
)

Write-Host "🚀 LUCID Infrastructure Reorganization Script" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
}

# Create backup directory if not dry run
if (-not $DryRun) {
    Write-Host "📦 Creating backup directory: $BackupDir" -ForegroundColor Blue
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

# Define the reorganization mapping
$ReorganizationMap = @{
    # Sessions components
    "sessions/recorder/Dockerfile.keystroke-monitor.distroless" = "infrastructure/docker/sessions/Dockerfile.keystroke-monitor.distroless"
    "sessions/recorder/Dockerfile.window-focus-monitor.distroless" = "infrastructure/docker/sessions/Dockerfile.window-focus-monitor.distroless"
    "sessions/recorder/Dockerfile.resource-monitor.distroless" = "infrastructure/docker/sessions/Dockerfile.resource-monitor.distroless"
    "sessions/recorder/Dockerfile.session-recorder" = "infrastructure/docker/sessions/Dockerfile.session-recorder"
    "sessions/core/Dockerfile.orchestrator" = "infrastructure/docker/sessions/Dockerfile.orchestrator"
    "sessions/core/Dockerfile.chunker" = "infrastructure/docker/sessions/Dockerfile.chunker"
    "sessions/core/Dockerfile.merkle_builder" = "infrastructure/docker/sessions/Dockerfile.merkle-builder"
    "sessions/encryption/Dockerfile.encryptor" = "infrastructure/docker/sessions/Dockerfile.encryptor"
    
    # RDP components
    "RDP/recorder/Dockerfile.rdp-host.distroless" = "infrastructure/docker/rdp/Dockerfile.rdp-host.distroless"
    "RDP/recorder/Dockerfile.clipboard-handler.distroless" = "infrastructure/docker/rdp/Dockerfile.clipboard-handler.distroless"
    "RDP/recorder/Dockerfile.file-transfer-handler.distroless" = "infrastructure/docker/rdp/Dockerfile.file-transfer-handler.distroless"
    "RDP/recorder/Dockerfile.wayland-integration.distroless" = "infrastructure/docker/rdp/Dockerfile.wayland-integration.distroless"
    "RDP/server/Dockerfile.server-manager" = "infrastructure/docker/rdp/Dockerfile.server-manager"
    "RDP/server/Dockerfile.server-manager.simple" = "infrastructure/docker/rdp/Dockerfile.server-manager.simple"
    "RDP/server/Dockerfile.xrdp-integration" = "infrastructure/docker/rdp/Dockerfile.xrdp-integration"
    
    # Wallet components
    "wallet/walletd/Dockerfile.software-vault.distroless" = "infrastructure/docker/wallet/Dockerfile.software-vault.distroless"
    "wallet/walletd/Dockerfile.role-manager.distroless" = "infrastructure/docker/wallet/Dockerfile.role-manager.distroless"
    "wallet/walletd/Dockerfile.key-rotation.distroless" = "infrastructure/docker/wallet/Dockerfile.key-rotation.distroless"
    
    # Blockchain components
    "blockchain/chain-client/Dockerfile.on-system-chain-client.distroless" = "infrastructure/docker/blockchain/Dockerfile.on-system-chain-client.distroless"
    "blockchain/chain-client/Dockerfile.lucid-anchors-client.distroless" = "infrastructure/docker/blockchain/Dockerfile.lucid-anchors-client.distroless"
    "blockchain/tron_node/Dockerfile.tron-client" = "infrastructure/docker/blockchain/Dockerfile.tron-client"
    "blockchain/on_system_chain/Dockerfile.chain-client" = "infrastructure/docker/blockchain/Dockerfile.chain-client"
    "blockchain/api/Dockerfile" = "infrastructure/docker/blockchain/Dockerfile.api"
    "blockchain/api/Dockerfile.distroless" = "infrastructure/docker/blockchain/Dockerfile.api.distroless"
    "blockchain/deployment/Dockerfile.contract-deployment" = "infrastructure/docker/blockchain/Dockerfile.contract-deployment"
    "blockchain/deployment/Dockerfile.contract-deployment.simple" = "infrastructure/docker/blockchain/Dockerfile.contract-deployment.simple"
    
    # Admin components
    "admin/admin-ui/Dockerfile.admin-ui.distroless" = "infrastructure/docker/admin/Dockerfile.admin-ui.distroless"
    "admin/ui/Dockerfile.admin-ui" = "infrastructure/docker/admin/Dockerfile.admin-ui"
    
    # Node components
    "node/consensus/Dockerfile.leader-selection.distroless" = "infrastructure/docker/node/Dockerfile.leader-selection.distroless"
    "node/consensus/Dockerfile.task-proofs.distroless" = "infrastructure/docker/node/Dockerfile.task-proofs.distroless"
    "node/dht_crdt/Dockerfile.dht-node" = "infrastructure/docker/node/Dockerfile.dht-node"
    
    # Common components
    "common/governance/Dockerfile.lucid-governor.distroless" = "infrastructure/docker/common/Dockerfile.lucid-governor.distroless"
    "common/governance/Dockerfile.timelock.distroless" = "infrastructure/docker/common/Dockerfile.timelock.distroless"
    "common/server-tools/Dockerfile" = "infrastructure/docker/common/Dockerfile.server-tools"
    "common/server-tools/Dockerfile.distroless" = "infrastructure/docker/common/Dockerfile.server-tools.distroless"
    
    # Payment systems
    "payment-systems/tron-node/Dockerfile.payout-router-v0.distroless" = "infrastructure/docker/payment-systems/Dockerfile.payout-router-v0.distroless"
    "payment-systems/tron-node/Dockerfile.usdt-trc20.distroless" = "infrastructure/docker/payment-systems/Dockerfile.usdt-trc20.distroless"
    
    # Tools
    "tools/ops/ota/Dockerfile.update-manager.distroless" = "infrastructure/docker/tools/Dockerfile.update-manager.distroless"
    "tools/ops/ota/Dockerfile.signature-verifier.distroless" = "infrastructure/docker/tools/Dockerfile.signature-verifier.distroless"
}

# Function to move Dockerfiles
function Move-Dockerfiles {
    foreach ($source in $ReorganizationMap.Keys) {
        $destination = $ReorganizationMap[$source]
        
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
        } else {
            Write-Host "⚠️  Source not found: $source" -ForegroundColor Yellow
        }
    }
}

# Main execution
Write-Host "🔄 Starting infrastructure reorganization..." -ForegroundColor Blue

# Step 1: Move Dockerfiles
Write-Host "`n📦 Step 1: Moving Dockerfiles to infrastructure directory" -ForegroundColor Blue
Move-Dockerfiles

Write-Host "`n🎉 Infrastructure reorganization complete!" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green

if (-not $DryRun) {
    Write-Host "📦 Backup created in: $BackupDir" -ForegroundColor Blue
    Write-Host "🚀 Run '.\scripts\rebuild-all-distroless.ps1' to rebuild all images" -ForegroundColor Blue
} else {
    Write-Host "🔍 This was a dry run - no changes were made" -ForegroundColor Yellow
    Write-Host "🚀 Run with -Force to execute the reorganization" -ForegroundColor Blue
}