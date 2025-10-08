# LUCID DISTROLESS IMAGE VERIFICATION SCRIPT
# Verifies all built images are available and properly tagged in Docker Hub

param(
    [string]$DockerRepo = "pickme/lucid",
    [switch]$Verbose = $false,
    [string]$LogFile = "verify-distroless-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
)

$ErrorActionPreference = "Stop"
$LogPath = Join-Path $PSScriptRoot $LogFile

function Write-Log {
    param($Message, $Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"
    Write-Host $LogEntry
    Add-Content -Path $LogPath -Value $LogEntry
}

function Test-ImageExists {
    param([string]$ImageTag)
    
    try {
        Write-Log "Checking image: $ImageTag" "INFO"
        $inspectOutput = docker buildx imagetools inspect $ImageTag 2>&1
        $inspectExitCode = $LASTEXITCODE
        
        if ($inspectExitCode -eq 0) {
            # Extract platform information
            $platforms = $inspectOutput | Where-Object { $_ -match "Platform:" } | ForEach-Object { ($_ -split ":")[1].Trim() }
            Write-Log "✓ Image exists: $ImageTag" "SUCCESS"
            Write-Log "  Platforms: $($platforms -join ', ')" "INFO"
            return $true
        } else {
            Write-Log "✗ Image not found: $ImageTag" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Exception during image check: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# All expected images based on build phases
$ExpectedImages = @(
    # Phase 1: Core Infrastructure
    "server-tools", "tunnel-tools", "tor-proxy",
    
    # Phase 2: API Gateway & Core Services
    "api-server", "api-gateway", "authentication",
    
    # Phase 3: Session Pipeline
    "session-chunker", "session-encryptor", "merkle-builder", "session-orchestrator",
    
    # Phase 4: Blockchain Core
    "blockchain-api", "blockchain-governance", "blockchain-ledger", 
    "blockchain-sessions-data", "blockchain-vm",
    
    # Phase 5: Payment Systems & Integration
    "tron-node-client", "payment-governance", "payment-distribution", "usdt-trc20",
    "payout-router-v0", "payout-router-kyc", "payment-analytics",
    "openapi-server", "openapi-gateway", "rdp-server-manager", "admin-ui"
)

Write-Log "=== LUCID DISTROLESS IMAGE VERIFICATION ===" "INFO"
Write-Log "Docker Repository: $DockerRepo" "INFO"
Write-Log "Expected Images: $($ExpectedImages.Count)" "INFO"
Write-Log "Log File: $LogPath" "INFO"

$verifiedCount = 0
$missingCount = 0
$missingImages = @()

foreach ($imageName in $ExpectedImages) {
    $imageTag = "${DockerRepo}:${imageName}"
    
    if (Test-ImageExists -ImageTag $imageTag) {
        $verifiedCount++
    } else {
        $missingCount++
        $missingImages += $imageName
    }
}

Write-Log "=== VERIFICATION SUMMARY ===" "INFO"
Write-Log "Total Images Expected: $($ExpectedImages.Count)" "INFO"
Write-Log "Images Verified: $verifiedCount" "INFO"
Write-Log "Images Missing: $missingCount" "INFO"
Write-Log "Verification Rate: $(($verifiedCount / $ExpectedImages.Count * 100).ToString('F2'))%" "INFO"

if ($missingCount -gt 0) {
    Write-Log "Missing Images:" "WARNING"
    foreach ($missing in $missingImages) {
        Write-Log "  - $missing" "WARNING"
    }
    Write-Log "Some images are missing. Please check the build process." "WARNING"
    exit 1
} else {
    Write-Log "All images verified successfully!" "SUCCESS"
    Write-Log "Ready for Raspberry Pi deployment." "SUCCESS"
    exit 0
}
