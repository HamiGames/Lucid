# LUCID Comprehensive Distroless Rebuild Script
# Rebuilds all distroless images with new infrastructure structure

Write-Host "🚀 LUCID Comprehensive Distroless Rebuild" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green

# Set build context to project root
$BuildContext = "."

# Define all distroless services
$Services = @(
    @{Name="keystroke-monitor"; Dockerfile="infrastructure/docker/sessions/Dockerfile.keystroke-monitor.distroless"},
    @{Name="window-focus-monitor"; Dockerfile="infrastructure/docker/sessions/Dockerfile.window-focus-monitor.distroless"},
    @{Name="resource-monitor"; Dockerfile="infrastructure/docker/sessions/Dockerfile.resource-monitor.distroless"},
    @{Name="session-recorder"; Dockerfile="infrastructure/docker/sessions/Dockerfile.session-recorder"},
    @{Name="orchestrator"; Dockerfile="infrastructure/docker/sessions/Dockerfile.orchestrator"},
    @{Name="chunker"; Dockerfile="infrastructure/docker/sessions/Dockerfile.chunker"},
    @{Name="merkle-builder"; Dockerfile="infrastructure/docker/sessions/Dockerfile.merkle-builder"},
    @{Name="encryptor"; Dockerfile="infrastructure/docker/sessions/Dockerfile.encryptor"},
    @{Name="rdp-host"; Dockerfile="infrastructure/docker/rdp/Dockerfile.rdp-host.distroless"},
    @{Name="clipboard-handler"; Dockerfile="infrastructure/docker/rdp/Dockerfile.clipboard-handler.distroless"},
    @{Name="file-transfer-handler"; Dockerfile="infrastructure/docker/rdp/Dockerfile.file-transfer-handler.distroless"},
    @{Name="wayland-integration"; Dockerfile="infrastructure/docker/rdp/Dockerfile.wayland-integration.distroless"},
    @{Name="server-manager"; Dockerfile="infrastructure/docker/rdp/Dockerfile.server-manager"},
    @{Name="xrdp-integration"; Dockerfile="infrastructure/docker/rdp/Dockerfile.xrdp-integration"},
    @{Name="software-vault"; Dockerfile="infrastructure/docker/wallet/Dockerfile.software-vault.distroless"},
    @{Name="role-manager"; Dockerfile="infrastructure/docker/wallet/Dockerfile.role-manager.distroless"},
    @{Name="key-rotation"; Dockerfile="infrastructure/docker/wallet/Dockerfile.key-rotation.distroless"},
    @{Name="on-system-chain-client"; Dockerfile="infrastructure/docker/blockchain/Dockerfile.on-system-chain-client.distroless"},
    @{Name="lucid-anchors-client"; Dockerfile="infrastructure/docker/blockchain/Dockerfile.lucid-anchors-client.distroless"},
    @{Name="tron-client"; Dockerfile="infrastructure/docker/blockchain/Dockerfile.tron-client"},
    @{Name="chain-client"; Dockerfile="infrastructure/docker/blockchain/Dockerfile.chain-client"},
    @{Name="blockchain-api"; Dockerfile="infrastructure/docker/blockchain/Dockerfile.api.distroless"},
    @{Name="contract-deployment"; Dockerfile="infrastructure/docker/blockchain/Dockerfile.contract-deployment"},
    @{Name="admin-ui"; Dockerfile="infrastructure/docker/admin/Dockerfile.admin-ui.distroless"},
    @{Name="leader-selection"; Dockerfile="infrastructure/docker/node/Dockerfile.leader-selection.distroless"},
    @{Name="task-proofs"; Dockerfile="infrastructure/docker/node/Dockerfile.task-proofs.distroless"},
    @{Name="dht-node"; Dockerfile="infrastructure/docker/node/Dockerfile.dht-node"},
    @{Name="lucid-governor"; Dockerfile="infrastructure/docker/common/Dockerfile.lucid-governor.distroless"},
    @{Name="timelock"; Dockerfile="infrastructure/docker/common/Dockerfile.timelock.distroless"},
    @{Name="server-tools"; Dockerfile="infrastructure/docker/common/Dockerfile.server-tools.distroless"},
    @{Name="payout-router-v0"; Dockerfile="infrastructure/docker/payment-systems/Dockerfile.payout-router-v0.distroless"},
    @{Name="usdt-trc20"; Dockerfile="infrastructure/docker/payment-systems/Dockerfile.usdt-trc20.distroless"},
    @{Name="update-manager"; Dockerfile="infrastructure/docker/tools/Dockerfile.update-manager.distroless"},
    @{Name="signature-verifier"; Dockerfile="infrastructure/docker/tools/Dockerfile.signature-verifier.distroless"}
)

# Build all services
foreach ($service in $Services) {
    Write-Host "`n🔨 Building $($service.Name)..." -ForegroundColor Blue
    Write-Host "   Dockerfile: $($service.Dockerfile)" -ForegroundColor Gray
    
    try {
        docker buildx build `
            --platform linux/amd64,linux/arm64 `
            --file $($service.Dockerfile) `
            --tag "pickme/lucid:$($service.Name)" `
            --tag "pickme/lucid:$($service.Name):latest" `
            --tag "pickme/lucid:$($service.Name):distroless" `
            --push `
            $BuildContext
        
        Write-Host "✅ Successfully built and pushed $($service.Name)" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to build $($service.Name): $_" -ForegroundColor Red
    }
}

Write-Host "`n🎉 All distroless images rebuilt and pushed to registry!" -ForegroundColor Green
