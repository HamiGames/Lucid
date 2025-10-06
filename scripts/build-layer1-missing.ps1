# LUCID Layer 1 Missing Images Build Script
# PowerShell script to build all missing Layer 1 distroless images
# Generated: 2025-10-05

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "LUCID Layer 1 Missing Images Build Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Set error handling
$ErrorActionPreference = "Stop"

# Build configuration
$DOCKER_REGISTRY = "pickme/lucid"
$BUILD_PLATFORMS = "linux/arm64,linux/amd64"
$BUILD_CONTEXT = "."

# Missing images to build
$MISSING_IMAGES = @(
    @{
        Name = "session-orchestrator"
        Dockerfile = "sessions/core/Dockerfile.orchestrator"
        Description = "Session Orchestrator - Main coordination layer"
    },
    @{
        Name = "blockchain-api"
        Dockerfile = "04-blockchain-core/api/Dockerfile"
        Description = "Blockchain API - Core blockchain operations"
    },
    @{
        Name = "blockchain-governance"
        Dockerfile = "04-blockchain-core/governance/Dockerfile"
        Description = "Blockchain Governance - Governance operations"
    },
    @{
        Name = "blockchain-sessions-data"
        Dockerfile = "04-blockchain-core/sessions-data/Dockerfile"
        Description = "Blockchain Sessions Data - Session data management"
    },
    @{
        Name = "blockchain-vm"
        Dockerfile = "04-blockchain-core/vm/Dockerfile"
        Description = "Blockchain Virtual Machine - VM operations"
    },
    @{
        Name = "blockchain-ledger"
        Dockerfile = "04-blockchain-core/ledger/Dockerfile"
        Description = "Blockchain Ledger - Ledger operations"
    }
)

# Function to build and push image
function Build-Image {
    param(
        [string]$ImageName,
        [string]$Dockerfile,
        [string]$Description
    )
    
    Write-Host "`n================================================" -ForegroundColor Yellow
    Write-Host "Building: $ImageName" -ForegroundColor Yellow
    Write-Host "Description: $Description" -ForegroundColor Yellow
    Write-Host "Dockerfile: $Dockerfile" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Yellow
    
    $ImageTag = "$DOCKER_REGISTRY`:$ImageName"
    
    try {
        # Build and push the image
        Write-Host "Building $ImageName..." -ForegroundColor Green
        docker buildx build `
            --platform $BUILD_PLATFORMS `
            --file $Dockerfile `
            --tag $ImageTag `
            --push `
            $BUILD_CONTEXT
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Successfully built and pushed: $ImageTag" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to build: $ImageName" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ Error building $ImageName`: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    return $true
}

# Main execution
Write-Host "Starting build process for $($MISSING_IMAGES.Count) missing images..." -ForegroundColor Cyan

$SuccessCount = 0
$FailureCount = 0
$StartTime = Get-Date

foreach ($Image in $MISSING_IMAGES) {
    $Result = Build-Image -ImageName $Image.Name -Dockerfile $Image.Dockerfile -Description $Image.Description
    
    if ($Result) {
        $SuccessCount++
    } else {
        $FailureCount++
    }
}

$EndTime = Get-Date
$Duration = $EndTime - $StartTime

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "Build Summary" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Total Images: $($MISSING_IMAGES.Count)" -ForegroundColor White
Write-Host "Successful: $SuccessCount" -ForegroundColor Green
Write-Host "Failed: $FailureCount" -ForegroundColor Red
Write-Host "Duration: $($Duration.ToString('hh\:mm\:ss'))" -ForegroundColor White

if ($FailureCount -eq 0) {
    Write-Host "`n🎉 All missing Layer 1 images built successfully!" -ForegroundColor Green
    Write-Host "You can now use the complete Layer 1 YAML file:" -ForegroundColor Cyan
    Write-Host "docker-compose -f infrastructure/compose/lucid-layer1-complete.yaml up -d" -ForegroundColor Yellow
} else {
    Write-Host "`n⚠️  Some images failed to build. Check the errors above." -ForegroundColor Yellow
}

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Verify images: docker images | grep pickme/lucid" -ForegroundColor White
Write-Host "2. Test Layer 1: docker-compose -f infrastructure/compose/lucid-layer1-complete.yaml up -d" -ForegroundColor White
Write-Host "3. Check logs: docker-compose -f infrastructure/compose/lucid-layer1-complete.yaml logs" -ForegroundColor White
