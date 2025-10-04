# LUCID STAGE 1 - BLOCKCHAIN GROUP DEPLOYMENT
# SPEC-4 Compliant Build & Deploy Sequence
# Generated: 2025-10-04 22:16:16 UTC
# Mode: LUCID-STRICT compliant
# Target: Stage 1 - Blockchain Group Services

[CmdletBinding()]
param(
    [switch]$DryRun = $false,
    [switch]$Force = $false,
    [switch]$SkipBuild = $false,
    [switch]$SkipPush = $false,
    [switch]$Help = $false
)

if ($Help) {
    Write-Host @"
LUCID STAGE 1 - BLOCKCHAIN GROUP DEPLOYMENT
==========================================

SERVICES INCLUDED:
- blockchain-core (validator/consensus node)
- blockchain-ledger (archival/state + snapshots)
- blockchain-virtual-machine (TVM/EVM-compatible contracts)
- blockchain-sessions-data (anchor event indexer)
- blockchain-governances (proposal/vote/timelock executor)

USAGE:
    .\stage1-blockchain-group-deploy.ps1 [OPTIONS]

OPTIONS:
    -DryRun      Show what would be built/deployed
    -Force       Skip confirmation prompts
    -SkipBuild   Skip building, just deploy existing images
    -SkipPush    Build but don't push to DockerHub
    -Help        Show this help message

EXAMPLES:
    .\stage1-blockchain-group-deploy.ps1
    .\stage1-blockchain-group-deploy.ps1 -DryRun
    .\stage1-blockchain-group-deploy.ps1 -Force
    .\stage1-blockchain-group-deploy.ps1 -SkipBuild -Force

TARGET ENVIRONMENT: /mnt/myssd/Lucid (Pi deployment)
DOCKERHUB REPO: pickme/lucid:blockchain-*
"@
    exit 0
}

# Color and formatting functions
function Write-StatusMessage {
    param($Message, $Type = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    switch ($Type) {
        "SUCCESS" { Write-Host "[$timestamp] [+] $Message" -ForegroundColor Green }
        "ERROR"   { Write-Host "[$timestamp] [!] $Message" -ForegroundColor Red }
        "WARNING" { Write-Host "[$timestamp] [-] $Message" -ForegroundColor Yellow }
        "INFO"    { Write-Host "[$timestamp] [i] $Message" -ForegroundColor Cyan }
        default   { Write-Host "[$timestamp] $Message" }
    }
}

function Write-Header {
    param($Title)
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Magenta
    Write-Host " $Title" -ForegroundColor Magenta
    Write-Host "=" * 70 -ForegroundColor Magenta
    Write-Host ""
}

# Error handling
$ErrorActionPreference = "Stop"
trap {
    Write-StatusMessage "CRITICAL ERROR: $($_.Exception.Message)" "ERROR"
    Write-StatusMessage "Script execution failed at line $($_.InvocationInfo.ScriptLineNumber)" "ERROR"
    exit 1
}

Write-Header "LUCID STAGE 1 - BLOCKCHAIN GROUP DEPLOYMENT"

# Verify project directory
Write-StatusMessage "Verifying LUCID-STRICT project environment..." "INFO"
if (-not (Test-Path ".git") -or -not (Test-Path "infrastructure") -or -not (Test-Path "04-blockchain-core")) {
    Write-StatusMessage "ERROR: Not in Lucid project root directory!" "ERROR"
    Write-StatusMessage "Please run from: C:\Users\surba\Desktop\personal\THE_FUCKER\lucid_2\Lucid" "ERROR"
    exit 1
}

Write-StatusMessage "Project directory verified: $(Get-Location)" "SUCCESS"

# Define Stage 1 Blockchain Group services
$BlockchainServices = @(
    @{
        Name = "blockchain-core"
        Path = "04-blockchain-core"
        Image = "pickme/lucid:blockchain-core"
        Description = "Validator/consensus node with block gossip"
    },
    @{
        Name = "blockchain-ledger"  
        Path = "04-blockchain-core/ledger"
        Image = "pickme/lucid:blockchain-ledger"
        Description = "Archival/state with snapshot tools"
    },
    @{
        Name = "blockchain-virtual-machine"
        Path = "04-blockchain-core/vm"
        Image = "pickme/lucid:blockchain-vm"
        Description = "TVM/EVM-compatible contract execution layer"
    },
    @{
        Name = "blockchain-sessions-data"
        Path = "04-blockchain-core/sessions-data"
        Image = "pickme/lucid:blockchain-sessions-data"
        Description = "Indexer for anchor events and manifest fields"
    },
    @{
        Name = "blockchain-governances"
        Path = "04-blockchain-core/governance"
        Image = "pickme/lucid:blockchain-governance"
        Description = "Proposal/vote/timelock executor with ParamRegistry"
    }
)

# Display services to be built
Write-StatusMessage "STAGE 1 BLOCKCHAIN GROUP - Services Overview:" "INFO"
Write-Host ""
Write-Host "BLOCKCHAIN SERVICES TO BUILD:" -ForegroundColor Yellow
Write-Host "-" * 50 -ForegroundColor Yellow
foreach ($service in $BlockchainServices) {
    $status = if (Test-Path $service.Path) { "READY" } else { "MISSING" }
    $color = if ($status -eq "READY") { "Green" } else { "Red" }
    Write-Host "  [$status] $($service.Name)" -ForegroundColor $color
    Write-Host "    Path: $($service.Path)" -ForegroundColor Gray
    Write-Host "    Image: $($service.Image)" -ForegroundColor Gray
    Write-Host "    Desc: $($service.Description)" -ForegroundColor Gray
    Write-Host ""
}

# Dry run mode
if ($DryRun) {
    Write-StatusMessage "DRY RUN MODE - No changes will be made" "WARNING"
    Write-Host ""
    Write-Host "WOULD EXECUTE:" -ForegroundColor Yellow
    
    if (-not $SkipBuild) {
        foreach ($service in $BlockchainServices) {
            Write-Host "  docker build -t $($service.Image) $($service.Path)/" -ForegroundColor Gray
        }
    }
    
    if (-not $SkipPush) {
        foreach ($service in $BlockchainServices) {
            Write-Host "  docker push $($service.Image)" -ForegroundColor Gray
        }
    }
    
    Write-Host "  # Generate Pi deployment commands" -ForegroundColor Gray
    Write-Host ""
    Write-StatusMessage "Dry run completed - no actual changes made" "INFO"
    exit 0
}

# Confirmation prompt (unless Force is used)
if (-not $Force) {
    Write-Host ""
    Write-Host "DEPLOYMENT DETAILS:" -ForegroundColor Magenta
    Write-Host "  Stage: 1 - Blockchain Group" -ForegroundColor White
    Write-Host "  Services: $($BlockchainServices.Count) blockchain services" -ForegroundColor White
    Write-Host "  Build: $(-not $SkipBuild)" -ForegroundColor White
    Write-Host "  Push to DockerHub: $(-not $SkipPush)" -ForegroundColor White
    Write-Host ""
    
    $confirm = Read-Host "Proceed with Stage 1 Blockchain Group deployment? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-StatusMessage "Operation cancelled by user" "WARNING"
        exit 0
    }
}

Write-Header "EXECUTING STAGE 1 BLOCKCHAIN GROUP BUILD"

# Build Stage 1 services
if (-not $SkipBuild) {
    Write-StatusMessage "Building Stage 1 Blockchain Group services..." "INFO"
    
    foreach ($service in $BlockchainServices) {
        Write-StatusMessage "Building $($service.Name)..." "INFO"
        
        if (-not (Test-Path $service.Path)) {
            Write-StatusMessage "WARNING: Path $($service.Path) not found, skipping $($service.Name)" "WARNING"
            continue
        }
        
        try {
            # Check for Dockerfile
            $dockerfilePath = Join-Path $service.Path "Dockerfile"
            if (-not (Test-Path $dockerfilePath)) {
                Write-StatusMessage "Creating basic Dockerfile for $($service.Name)..." "INFO"
                $dockerfileContent = @"
# LUCID $($service.Name.ToUpper()) - SPEC-4 Compliant
FROM pickme/lucid:devcontainer-dind as base

LABEL org.lucid.plane="chain"
LABEL org.lucid.service="$($service.Name)"
LABEL org.lucid.stage="1"
LABEL org.lucid.expose="true"

WORKDIR /workspaces/Lucid

# Copy service-specific files
COPY . /workspaces/Lucid/$($service.Path)/

# Install dependencies
RUN cd $($service.Path) && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    if [ -f package.json ]; then npm install; fi

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Entry point
EXPOSE 8080
CMD ["python", "$($service.Path)/main.py"]
"@
                Set-Content -Path $dockerfilePath -Value $dockerfileContent
            }
            
            # Build with BuildKit
            $env:DOCKER_BUILDKIT = "1"
            docker build --platform linux/amd64,linux/arm64 -t $service.Image $service.Path
            Write-StatusMessage "$($service.Name) built successfully" "SUCCESS"
            
        } catch {
            Write-StatusMessage "Failed to build $($service.Name): $($_.Exception.Message)" "ERROR"
            if (-not $Force) {
                exit 1
            }
        }
    }
} else {
    Write-StatusMessage "Skipping build phase (as requested)" "WARNING"
}

# Push to DockerHub
if (-not $SkipPush) {
    Write-Header "PUSHING STAGE 1 IMAGES TO DOCKERHUB"
    
    foreach ($service in $BlockchainServices) {
        Write-StatusMessage "Pushing $($service.Name) to DockerHub..." "INFO"
        
        try {
            docker push $service.Image
            Write-StatusMessage "$($service.Name) pushed successfully" "SUCCESS"
        } catch {
            Write-StatusMessage "Failed to push $($service.Name): $($_.Exception.Message)" "ERROR"
            if (-not $Force) {
                exit 1
            }
        }
    }
} else {
    Write-StatusMessage "Skipping push phase (as requested)" "WARNING"
}

# Generate Pi deployment commands for Stage 1
Write-Header "GENERATING PI DEPLOYMENT COMMANDS"

$piCommands = @"
# LUCID STAGE 1 - BLOCKCHAIN GROUP PI DEPLOYMENT
# Target: pickme@192.168.0.75
# Path: /mnt/myssd/Lucid
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss UTC")

# SSH to Pi
ssh pickme@192.168.0.75

# Navigate to project
cd /mnt/myssd/Lucid

# Pull latest changes
git pull origin main

# Pull Stage 1 Blockchain Group images
"@

foreach ($service in $BlockchainServices) {
    $piCommands += "`ndocker pull $($service.Image)"
}

$piCommands += @"

# Start Stage 1 services with profile
docker-compose -f infrastructure/compose/lucid-dev.yaml --profile blockchain up -d

# Verify blockchain services
docker ps --filter "label=org.lucid.stage=1" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health check Stage 1 services
"@

foreach ($service in $BlockchainServices) {
    $piCommands += "`ndocker exec $($service.Name) curl -f http://localhost:8080/health || echo '$($service.Name) health check failed'"
}

$piCommands += @"

# Check blockchain consensus status
docker logs blockchain-core --tail=50

# Verify governance hooks
docker logs blockchain-governances --tail=20

# Exit SSH
exit
"@

# Save Pi deployment commands
$piCommandsFile = "progress/STAGE1_BLOCKCHAIN_PI_DEPLOYMENT_$(Get-Date -Format 'yyyyMMdd-HHmmss').md"
Set-Content -Path $piCommandsFile -Value $piCommands
Write-StatusMessage "Pi deployment commands saved to: $piCommandsFile" "SUCCESS"

Write-Header "STAGE 1 BLOCKCHAIN GROUP DEPLOYMENT COMPLETED"

Write-StatusMessage "Stage 1 Blockchain Group deployment completed successfully!" "SUCCESS"
Write-Host ""
Write-Host "BLOCKCHAIN SERVICES DEPLOYED:" -ForegroundColor Green
foreach ($service in $BlockchainServices) {
    Write-Host "  [+] $($service.Name) -> $($service.Image)" -ForegroundColor Green
}

Write-Host ""
Write-StatusMessage "Next Steps:" "INFO"
Write-StatusMessage "1. Execute Pi deployment commands from: $piCommandsFile" "INFO"
Write-StatusMessage "2. Verify blockchain consensus is stable" "INFO"
Write-StatusMessage "3. Proceed to Stage 2 - Sessions Group" "INFO"
Write-Host ""
Write-StatusMessage "STAGE 1 BLOCKCHAIN GROUP READY FOR PI DEPLOYMENT!" "SUCCESS"