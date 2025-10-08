# LUCID DISTROLESS BUILD SCRIPT - PHASES 2-5 ONLY
# Builds and pushes distroless images for phases 2, 3, 4, and 5
# Skips Phase 1 (Core Infrastructure) - assumes already built
# Target: Raspberry Pi deployment via Docker Hub

param(
    [string]$DockerRepo = "pickme/lucid",
    [string]$Platforms = "linux/arm64,linux/amd64",
    [switch]$SkipPush = $false,
    [switch]$Verbose = $false,
    [string]$LogFile = "build-phases-2-5-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
)

# Error handling and logging setup
$ErrorActionPreference = "Stop"
$LogPath = Join-Path $PSScriptRoot $LogFile

function Write-Log {
    param($Message, $Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"
    Write-Host $LogEntry
    Add-Content -Path $LogPath -Value $LogEntry
}

function Test-DockerBuildx {
    try {
        $buildxVersion = docker buildx version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Docker Buildx not available"
        }
        Write-Log "Docker Buildx available: $($buildxVersion[0])" "INFO"
        return $true
    }
    catch {
        Write-Log "Docker Buildx not found. Please install Docker Buildx." "ERROR"
        return $false
    }
}

function Initialize-BuildxBuilder {
    try {
        Write-Log "Initializing Docker Buildx builder..." "INFO"
        
        # Create builder if it doesn't exist
        $builderExists = docker buildx ls --format "{{.Name}}" | Where-Object { $_ -eq "lucid-builder" }
        if (-not $builderExists) {
            docker buildx create --name lucid-builder --use
            Write-Log "Created new buildx builder: lucid-builder" "INFO"
        } else {
            docker buildx use lucid-builder
            Write-Log "Using existing buildx builder: lucid-builder" "INFO"
        }
        
        # Bootstrap the builder
        docker buildx inspect --bootstrap
        Write-Log "Buildx builder initialized successfully" "INFO"
        return $true
    }
    catch {
        Write-Log "Failed to initialize buildx builder: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Build-DistrolessImage {
    param(
        [string]$ServiceName,
        [string]$ServicePath,
        [string]$Dockerfile,
        [string]$Phase
    )
    
    $tag = "${DockerRepo}:${ServiceName}"
    $dockerfilePath = Join-Path $ServicePath $Dockerfile
    
    Write-Log "Building Phase $Phase - Service: $ServiceName" "INFO"
    Write-Log "  Path: $ServicePath" "INFO"
    Write-Log "  Dockerfile: $dockerfilePath" "INFO"
    Write-Log "  Tag: $tag" "INFO"
    
    # Check if Dockerfile exists
    if (-not (Test-Path $dockerfilePath)) {
        Write-Log "Dockerfile not found: $dockerfilePath" "WARNING"
        return $false
    }
    
    # Check if service directory exists
    if (-not (Test-Path $ServicePath)) {
        Write-Log "Service directory not found: $ServicePath" "WARNING"
        return $false
    }
    
    try {
        $buildArgs = @(
            "buildx", "build",
            "--platform", $Platforms,
            "-f", $dockerfilePath,
            "-t", $tag
        )
        
        if (-not $SkipPush) {
            $buildArgs += "--push"
        }
        
        $buildArgs += $ServicePath
        
        if ($Verbose) {
            Write-Log "Build command: docker $($buildArgs -join ' ')" "DEBUG"
        }
        
        $buildOutput = & docker @buildArgs 2>&1
        $buildExitCode = $LASTEXITCODE
        
        if ($buildExitCode -eq 0) {
            Write-Log "✓ Successfully built: $tag" "SUCCESS"
            if ($Verbose) {
                Write-Log "Build output: $buildOutput" "DEBUG"
            }
            return $true
        } else {
            Write-Log "✗ Failed to build: $ServiceName (Exit code: $buildExitCode)" "ERROR"
            Write-Log "Build output: $buildOutput" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Exception during build of $ServiceName : $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Verify-Image {
    param([string]$ImageTag)
    
    try {
        if ($SkipPush) {
            Write-Log "Skipping image verification (local build only)" "INFO"
            return $true
        }
        
        Write-Log "Verifying image: $ImageTag" "INFO"
        $inspectOutput = docker buildx imagetools inspect $ImageTag 2>&1
        $inspectExitCode = $LASTEXITCODE
        
        if ($inspectExitCode -eq 0) {
            Write-Log "✓ Image verified: $ImageTag" "SUCCESS"
            return $true
        } else {
            Write-Log "✗ Image verification failed: $ImageTag" "ERROR"
            Write-Log "Inspect output: $inspectOutput" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Exception during image verification: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# PHASE DEFINITIONS - PHASES 2-5 ONLY
$BuildPhases = @{
    "Phase2" = @{
        Name = "API Gateway & Core Services"
        Description = "API infrastructure and core application services"
        Services = @(
            @{Name="api-server"; Path="03-api-gateway/api"; Dockerfile="Dockerfile.distroless"},
            @{Name="api-gateway"; Path="03-api-gateway/gateway"; Dockerfile="Dockerfile.distroless"},
            @{Name="authentication"; Path="auth"; Dockerfile="Dockerfile.authentication.distroless"}
        )
    }
    "Phase3" = @{
        Name = "Session Pipeline"
        Description = "Session processing, encryption, and Merkle tree building"
        Services = @(
            @{Name="session-chunker"; Path="sessions/core"; Dockerfile="Dockerfile.chunker.distroless"},
            @{Name="session-encryptor"; Path="sessions/encryption"; Dockerfile="Dockerfile.encryptor.distroless"},
            @{Name="merkle-builder"; Path="sessions/core"; Dockerfile="Dockerfile.merkle_builder.distroless"},
            @{Name="session-orchestrator"; Path="sessions/core"; Dockerfile="Dockerfile.orchestrator.distroless"}
        )
    }
    "Phase4" = @{
        Name = "Blockchain Core"
        Description = "Blockchain services, governance, and VM components"
        Services = @(
            @{Name="blockchain-api"; Path="04-blockchain-core/api"; Dockerfile="Dockerfile.distroless"},
            @{Name="blockchain-governance"; Path="04-blockchain-core/governance"; Dockerfile="Dockerfile.distroless"},
            @{Name="blockchain-ledger"; Path="04-blockchain-core/ledger"; Dockerfile="Dockerfile.distroless"},
            @{Name="blockchain-sessions-data"; Path="04-blockchain-core/sessions-data"; Dockerfile="Dockerfile.distroless"},
            @{Name="blockchain-vm"; Path="04-blockchain-core/vm"; Dockerfile="Dockerfile.distroless"}
        )
    }
    "Phase5" = @{
        Name = "Payment Systems & Integration"
        Description = "TRON integration, payment processing, and external services"
        Services = @(
            @{Name="tron-node-client"; Path="payment-systems/tron-node"; Dockerfile="Dockerfile.distroless"},
            @{Name="payment-governance"; Path="payment-systems/governance"; Dockerfile="Dockerfile.distroless"},
            @{Name="payment-distribution"; Path="payment-systems/distribution"; Dockerfile="Dockerfile.distroless"},
            @{Name="usdt-trc20"; Path="payment-systems/usdt"; Dockerfile="Dockerfile.distroless"},
            @{Name="payout-router-v0"; Path="payment-systems/payout-v0"; Dockerfile="Dockerfile.distroless"},
            @{Name="payout-router-kyc"; Path="payment-systems/payout-kyc"; Dockerfile="Dockerfile.distroless"},
            @{Name="payment-analytics"; Path="payment-systems/analytics"; Dockerfile="Dockerfile.distroless"},
            @{Name="openapi-server"; Path="open-api/api"; Dockerfile="Dockerfile.distroless"},
            @{Name="openapi-gateway"; Path="open-api/gateway"; Dockerfile="Dockerfile.distroless"},
            @{Name="rdp-server-manager"; Path="RDP/server"; Dockerfile="Dockerfile.distroless"},
            @{Name="admin-ui"; Path="admin/ui"; Dockerfile="Dockerfile.distroless"}
        )
    }
}

# MAIN EXECUTION
Write-Log "=== LUCID DISTROLESS BUILD SCRIPT - PHASES 2-5 ===" "INFO"
Write-Log "Docker Repository: $DockerRepo" "INFO"
Write-Log "Platforms: $Platforms" "INFO"
Write-Log "Skip Push: $SkipPush" "INFO"
Write-Log "Log File: $LogPath" "INFO"
Write-Log "NOTE: Phase 1 (Core Infrastructure) is skipped - assuming already built" "INFO"

# Pre-flight checks
Write-Log "Performing pre-flight checks..." "INFO"

if (-not (Test-DockerBuildx)) {
    Write-Log "Pre-flight check failed: Docker Buildx not available" "ERROR"
    exit 1
}

if (-not (Initialize-BuildxBuilder)) {
    Write-Log "Pre-flight check failed: Could not initialize buildx builder" "ERROR"
    exit 1
}

# Login to Docker Hub if pushing
if (-not $SkipPush) {
    Write-Log "Please ensure you are logged into Docker Hub (docker login)" "INFO"
    Write-Log "Press any key to continue or Ctrl+C to cancel..." "INFO"
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Build each phase
$totalServices = 0
$successfulBuilds = 0
$failedBuilds = 0

foreach ($phaseKey in $BuildPhases.Keys | Sort-Object) {
    $phase = $BuildPhases[$phaseKey]
    $phaseNumber = $phaseKey -replace "Phase", ""
    
    Write-Log "=== $phaseKey : $($phase.Name) ===" "INFO"
    Write-Log "Description: $($phase.Description)" "INFO"
    Write-Log "Services in this phase: $($phase.Services.Count)" "INFO"
    
    $phaseStartTime = Get-Date
    
    foreach ($service in $phase.Services) {
        $totalServices++
        $serviceStartTime = Get-Date
        
        Write-Log "Building service $totalServices of $($BuildPhases.Values | ForEach-Object { $_.Services.Count } | Measure-Object -Sum).Sum" "INFO"
        
        $buildSuccess = Build-DistrolessImage -ServiceName $service.Name -ServicePath $service.Path -Dockerfile $service.Dockerfile -Phase $phaseNumber
        
        if ($buildSuccess) {
            $successfulBuilds++
            
            # Verify image if pushing
            if (-not $SkipPush) {
                $verifySuccess = Verify-Image -ImageTag "${DockerRepo}:$($service.Name)"
                if (-not $verifySuccess) {
                    Write-Log "Image verification failed for: $($service.Name)" "WARNING"
                }
            }
        } else {
            $failedBuilds++
            Write-Log "Build failed for service: $($service.Name)" "ERROR"
        }
        
        $serviceDuration = (Get-Date) - $serviceStartTime
        Write-Log "Service build completed in: $($serviceDuration.TotalSeconds.ToString('F2')) seconds" "INFO"
    }
    
    $phaseDuration = (Get-Date) - $phaseStartTime
    Write-Log "=== $phaseKey COMPLETED in $($phaseDuration.TotalMinutes.ToString('F2')) minutes ===" "INFO"
    Write-Log "Phase Summary - Successful: $($phase.Services.Count - ($failedBuilds - ($totalServices - $phase.Services.Count))), Failed: $($failedBuilds - ($totalServices - $phase.Services.Count))" "INFO"
}

# Final summary
$totalDuration = (Get-Date) - $script:StartTime
Write-Log "=== BUILD SUMMARY - PHASES 2-5 ===" "INFO"
Write-Log "Total Services: $totalServices" "INFO"
Write-Log "Successful Builds: $successfulBuilds" "INFO"
Write-Log "Failed Builds: $failedBuilds" "INFO"
Write-Log "Success Rate: $(($successfulBuilds / $totalServices * 100).ToString('F2'))%" "INFO"
Write-Log "Total Duration: $($totalDuration.TotalMinutes.ToString('F2')) minutes" "INFO"

if ($failedBuilds -gt 0) {
    Write-Log "Some builds failed. Check the log file for details: $LogPath" "WARNING"
    exit 1
} else {
    Write-Log "All phases 2-5 distroless images built and pushed successfully!" "SUCCESS"
    Write-Log "Images are now available in Docker Hub repository: $DockerRepo" "SUCCESS"
    Write-Log "Ready for deployment with existing Phase 1 infrastructure." "SUCCESS"
    exit 0
}

# Set script start time
$script:StartTime = Get-Date
