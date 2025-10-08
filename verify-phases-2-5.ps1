# LUCID DISTROLESS IMAGE VERIFICATION SCRIPT - PHASES 2-5
# Verifies all built images for phases 2-5 are available and properly tagged in Docker Hub

param(
    [string]$DockerRepo = "pickme/lucid",
    [switch]$Verbose = $false,
    [string]$LogFile = "verify-phases-2-5-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
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

# Expected images for phases 2-5 only
$ExpectedImages = @{
    "Phase2" = @{
        Name = "API Gateway & Core Services"
        Images = @("api-server", "api-gateway", "authentication")
    }
    "Phase3" = @{
        Name = "Session Pipeline"
        Images = @("session-chunker", "session-encryptor", "merkle-builder", "session-orchestrator")
    }
    "Phase4" = @{
        Name = "Blockchain Core"
        Images = @("blockchain-api", "blockchain-governance", "blockchain-ledger", "blockchain-sessions-data", "blockchain-vm")
    }
    "Phase5" = @{
        Name = "Payment Systems & Integration"
        Images = @("tron-node-client", "payment-governance", "payment-distribution", "usdt-trc20", "payout-router-v0", "payout-router-kyc", "payment-analytics", "openapi-server", "openapi-gateway", "rdp-server-manager", "admin-ui")
    }
}

Write-Log "=== LUCID DISTROLESS IMAGE VERIFICATION - PHASES 2-5 ===" "INFO"
Write-Log "Docker Repository: $DockerRepo" "INFO"
Write-Log "Log File: $LogPath" "INFO"

$totalImages = 0
$verifiedCount = 0
$missingCount = 0
$phaseResults = @{}

# Calculate total images
foreach ($phase in $ExpectedImages.Values) {
    $totalImages += $phase.Images.Count
}

Write-Log "Total Images Expected: $totalImages" "INFO"
Write-Log "NOTE: Phase 1 images (server-tools, tunnel-tools, tor-proxy) are not verified" "INFO"

# Verify each phase
foreach ($phaseKey in $ExpectedImages.Keys | Sort-Object) {
    $phase = $ExpectedImages[$phaseKey]
    $phaseNumber = $phaseKey -replace "Phase", ""
    
    Write-Log "=== Verifying $phaseKey : $($phase.Name) ===" "INFO"
    
    $phaseVerified = 0
    $phaseMissing = 0
    $phaseMissingImages = @()
    
    foreach ($imageName in $phase.Images) {
        $imageTag = "${DockerRepo}:${imageName}"
        
        if (Test-ImageExists -ImageTag $imageTag) {
            $verifiedCount++
            $phaseVerified++
        } else {
            $missingCount++
            $phaseMissing++
            $phaseMissingImages += $imageName
        }
    }
    
    $phaseResults[$phaseKey] = @{
        Verified = $phaseVerified
        Missing = $phaseMissing
        MissingImages = $phaseMissingImages
    }
    
    Write-Log "Phase $phaseNumber Summary - Verified: $phaseVerified, Missing: $phaseMissing" "INFO"
    if ($phaseMissing -gt 0) {
        Write-Log "Missing images: $($phaseMissingImages -join ', ')" "WARNING"
    }
}

Write-Log "=== VERIFICATION SUMMARY - PHASES 2-5 ===" "INFO"
Write-Log "Total Images Expected: $totalImages" "INFO"
Write-Log "Images Verified: $verifiedCount" "INFO"
Write-Log "Images Missing: $missingCount" "INFO"
Write-Log "Verification Rate: $(($verifiedCount / $totalImages * 100).ToString('F2'))%" "INFO"

# Detailed phase breakdown
Write-Log "=== PHASE BREAKDOWN ===" "INFO"
foreach ($phaseKey in $ExpectedImages.Keys | Sort-Object) {
    $phase = $ExpectedImages[$phaseKey]
    $phaseNumber = $phaseKey -replace "Phase", ""
    $result = $phaseResults[$phaseKey]
    
    Write-Log "Phase $phaseNumber ($($phase.Name)): $($result.Verified)/$($phase.Images.Count) verified" "INFO"
    if ($result.Missing -gt 0) {
        Write-Log "  Missing: $($result.MissingImages -join ', ')" "WARNING"
    }
}

if ($missingCount -gt 0) {
    Write-Log "Some images are missing. Please check the build process." "WARNING"
    Write-Log "Missing images by phase:" "WARNING"
    foreach ($phaseKey in $ExpectedImages.Keys | Sort-Object) {
        $result = $phaseResults[$phaseKey]
        if ($result.Missing -gt 0) {
            Write-Log "  $phaseKey : $($result.MissingImages -join ', ')" "WARNING"
        }
    }
    exit 1
} else {
    Write-Log "All phases 2-5 images verified successfully!" "SUCCESS"
    Write-Log "Ready for deployment with existing Phase 1 infrastructure." "SUCCESS"
    exit 0
}
