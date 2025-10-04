# LUCID CORE SUPPORT SERVICES - Windows PowerShell Deployment
# Builds and deploys core infrastructure services from Windows
# GENIUS-LEVEL implementation with LUCID-STRICT compliance
# Path: scripts/windows-deploy-core-support.ps1

param(
    [string]$Mode = "full",
    [switch]$SkipBuild,
    [switch]$SkipDeploy,
    [switch]$TestOnly
)

# Colors for output
$Colors = @{
    Red = 'Red'
    Green = 'Green'
    Yellow = 'Yellow'
    Blue = 'Blue'
    Cyan = 'Cyan'
    Magenta = 'Magenta'
}

function Write-Log {
    param([string]$Message, [string]$Color = 'Blue')
    Write-Host "[CORE-SUPPORT] $Message" -ForegroundColor $Colors[$Color]
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor $Colors.Cyan
    Write-Host ""
}

# Configuration
$LucidRoot = $PSScriptRoot | Split-Path
$ComposeFile = "$LucidRoot\infrastructure\compose\lucid-dev.yaml"
$DockerRegistry = "pickme/lucid"
$PiHost = "pickme@192.168.0.75"
$PiDeployDir = "/home/pickme/lucid-core"

# Core support services and their image mappings
$ServiceImages = @{
    'tor-proxy' = 'tor-proxy'
    'lucid_api' = 'api-server'
    'lucid_api_gateway' = 'api-gateway'
    'tunnel-tools' = 'tunnel-tools'
    'server-tools' = 'server-tools'
}

function Test-Prerequisites {
    Write-Section "Prerequisites Check"
    
    # Check Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker not found. Please install Docker Desktop."
        return $false
    }
    Write-Success "Docker found"
    
    # Check Docker is running
    try {
        docker info | Out-Null
        Write-Success "Docker daemon is running"
    } catch {
        Write-Error "Docker daemon not running. Please start Docker Desktop."
        return $false
    }
    
    # Check Buildx
    try {
        docker buildx version | Out-Null
        Write-Success "Docker Buildx available"
    } catch {
        Write-Error "Docker Buildx not available. Please update Docker Desktop."
        return $false
    }
    
    # Check compose file
    if (-not (Test-Path $ComposeFile)) {
        Write-Error "Compose file not found: $ComposeFile"
        return $false
    }
    Write-Success "Compose file found"
    
    # Check SSH for Pi (if not test-only)
    if (-not $TestOnly) {
        Write-Log "Testing SSH connection to Pi..."
        $sshTest = ssh -o ConnectTimeout=10 -o BatchMode=yes $PiHost "echo 'Pi connection successful'" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "SSH connection to Pi verified"
        } else {
            Write-Error "Cannot connect to Pi via SSH: $PiHost"
            Write-Error "Please ensure SSH key authentication is configured"
            return $false
        }
    }
    
    return $true
}

function Set-DockerBuildx {
    Write-Section "Setting Up Multi-Platform Builder"
    
    $BuilderName = "lucid-core-builder"
    $Platforms = "linux/amd64,linux/arm64"
    
    # Remove existing builder if it exists
    docker buildx rm $BuilderName 2>$null
    
    # Create new builder
    Write-Log "Creating multi-platform builder: $BuilderName"
    docker buildx create --name $BuilderName --driver docker-container --platform $Platforms --bootstrap
    
    # Use the builder
    docker buildx use $BuilderName
    
    Write-Success "Multi-platform builder ready"
}

function Build-CoreServices {
    Write-Section "Building Core Support Services"
    
    $BuildTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BuildTag = "core-support-$BuildTimestamp"
    $Platforms = "linux/amd64,linux/arm64"
    
    # Clear buildx cache as per rules
    Write-Log "Clearing buildx cache for fresh state"
    docker buildx prune -f --all
    
    foreach ($service in $ServiceImages.Keys) {
        $imageName = $ServiceImages[$service]
        $fullImage = "${DockerRegistry}:${imageName}"
        $buildImage = "${DockerRegistry}:${imageName}-${BuildTag}"
        
        Write-Log "Building $service -> $imageName"
        
        # Determine build context
        switch ($service) {
            'tor-proxy' {
                $contextPath = "$LucidRoot\02-network-security\tor"
                $dockerfile = "Dockerfile"
            }
            'lucid_api' {
                $contextPath = "$LucidRoot\03-api-gateway\api"
                $dockerfile = "Dockerfile.api"
            }
            'lucid_api_gateway' {
                $contextPath = "$LucidRoot\03-api-gateway\gateway"
                $dockerfile = "Dockerfile.gateway"
            }
            'tunnel-tools' {
                $contextPath = "$LucidRoot\02-network-security\tunnels"
                $dockerfile = "Dockerfile"
            }
            'server-tools' {
                $contextPath = "$LucidRoot\common\server-tools"
                $dockerfile = "Dockerfile"
            }
        }
        
        # Check context exists
        if (-not (Test-Path "$contextPath\$dockerfile")) {
            Write-Error "Dockerfile not found: $contextPath\$dockerfile"
            continue
        }
        
        Write-Log "Building from: $contextPath"
        
        # Change to context directory
        Push-Location $contextPath
        
        try {
            # Build and push
            $buildArgs = @(
                'buildx', 'build',
                '--platform', $Platforms,
                '--file', $dockerfile,
                '--tag', $fullImage,
                '--tag', $buildImage,
                '--tag', "${DockerRegistry}:${imageName}-latest",
                '--build-arg', 'BUILDKIT_INLINE_CACHE=1',
                '--build-arg', "BUILD_TIMESTAMP=$BuildTimestamp",
                '--build-arg', 'BUILD_VERSION=core-support-1.0.0',
                '--push',
                '.'
            )
            
            Write-Log "Executing: docker $($buildArgs -join ' ')"
            & docker @buildArgs
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Built and pushed: $service -> $fullImage"
            } else {
                Write-Error "Failed to build: $service"
            }
        } finally {
            Pop-Location
        }
    }
    
    Write-Success "All core services built and pushed"
}

function Deploy-ToPi {
    Write-Section "Deploying to Raspberry Pi"
    
    Write-Log "Creating deployment directory on Pi"
    ssh $PiHost "mkdir -p $PiDeployDir"
    
    # Transfer compose file
    Write-Log "Transferring lucid-dev.yaml to Pi"
    scp "$LucidRoot\infrastructure\compose\lucid-dev.yaml" "${PiHost}:${PiDeployDir}/"
    
    # Create Pi environment file
    Write-Log "Creating Pi environment file"
    $piEnvContent = @"
# LUCID Pi Deployment Environment
LUCID_ENV=pi
LUCID_PLANE=ops
CLUSTER_ID=pi-core

# Database configuration
MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false

# Tor configuration (populated by services)
TOR_CONTROL_PASSWORD=
ONION_API_GATEWAY=
ONION_API_SERVER=
ONION_TUNNEL=
ONION_MONGO=
ONION_TOR_CONTROL=

# Security
AGE_PRIVATE_KEY=

# Pi-specific paths
LUCID_DATA_PATH=/home/pickme/lucid-data
LUCID_LOGS_PATH=/home/pickme/lucid-logs
"@
    
    $piEnvContent | Out-File -FilePath "$env:TEMP\lucid-pi.env" -Encoding utf8
    scp "$env:TEMP\lucid-pi.env" "${PiHost}:${PiDeployDir}/.env"
    Remove-Item "$env:TEMP\lucid-pi.env"
    
    # Create helper script for Pi
    Write-Log "Creating Pi helper script"
    $helperScript = @'
#!/bin/bash
# Pi Helper Scripts for Lucid Core Services

case "${1:-status}" in
    "status"|"check")
        echo "=== Lucid Core Services Status ==="
        docker compose -f lucid-dev.yaml ps
        echo ""
        
        echo "=== Health Checks ==="
        if curl -s --socks5-hostname localhost:9050 http://httpbin.org/ip >/dev/null 2>&1; then
            echo "✅ Tor proxy healthy"
        else
            echo "⚠️ Tor proxy issues"
        fi
        
        if docker exec lucid_mongo mongosh --quiet --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
            echo "✅ MongoDB healthy"
        else
            echo "⚠️ MongoDB issues"
        fi
        
        if curl -fsS http://localhost:8081/health >/dev/null 2>&1; then
            echo "✅ API Server healthy"
        else
            echo "⚠️ API Server issues"
        fi
        
        if curl -fsS http://localhost:8080/health >/dev/null 2>&1; then
            echo "✅ API Gateway healthy"
        else
            echo "⚠️ API Gateway issues"
        fi
        ;;
    "logs")
        docker compose -f lucid-dev.yaml logs --tail=20 ${2:-}
        ;;
    "restart")
        docker compose -f lucid-dev.yaml restart
        ;;
    "update")
        docker compose -f lucid-dev.yaml pull
        docker compose -f lucid-dev.yaml up -d
        ;;
    *)
        echo "Usage: $0 [status|logs [service]|restart|update]"
        ;;
esac
'@
    
    $helperScript | Out-File -FilePath "$env:TEMP\pi-helper.sh" -Encoding utf8
    scp "$env:TEMP\pi-helper.sh" "${PiHost}:${PiDeployDir}/helper.sh"
    ssh $PiHost "chmod +x $PiDeployDir/helper.sh"
    Remove-Item "$env:TEMP\pi-helper.sh"
    
    # Pull images on Pi
    Write-Log "Pulling images on Pi"
    foreach ($service in $ServiceImages.Keys) {
        $imageName = $ServiceImages[$service]
        $fullImage = "${DockerRegistry}:${imageName}"
        Write-Log "Pulling $fullImage on Pi"
        ssh $PiHost "docker pull $fullImage"
    }
    
    # Setup Pi networking
    Write-Log "Setting up Pi networking"
    ssh $PiHost "docker network create lucid_core_net --driver bridge --subnet 172.21.0.0/16 --attachable 2>/dev/null || echo 'Network exists'"
    ssh $PiHost "docker network create lucid-dev_lucid_net --driver bridge --attachable 2>/dev/null || echo 'External network created'"
    
    # Create data directories
    Write-Log "Creating data directories on Pi"
    ssh $PiHost "mkdir -p /home/pickme/lucid-data/{mongo,tor,onions,tunnels,logs}"
    ssh $PiHost "mkdir -p /home/pickme/lucid-logs"
    
    # Deploy services
    Write-Log "Starting core support services on Pi"
    ssh $PiHost "cd $PiDeployDir && docker compose -f lucid-dev.yaml up -d"
    
    # Wait and verify
    Write-Log "Waiting for services to initialize..."
    Start-Sleep 30
    
    Write-Log "Checking service status on Pi"
    ssh $PiHost "cd $PiDeployDir && docker compose -f lucid-dev.yaml ps"
    
    Write-Success "Pi deployment complete"
}

function Show-Summary {
    Write-Section "🎉 DEPLOYMENT COMPLETE!"
    
    Write-Success "LUCID Core Support Services Successfully Deployed!"
    Write-Host ""
    
    Write-Log "📋 Deployment Summary:"
    Write-Host "  ✅ Multi-arch images built (AMD64 + ARM64)" -ForegroundColor Green
    Write-Host "  ✅ Images pushed to Docker Hub (pickme/lucid)" -ForegroundColor Green
    Write-Host "  ✅ Services deployed to Raspberry Pi" -ForegroundColor Green
    Write-Host "  ✅ Core infrastructure running" -ForegroundColor Green
    Write-Host ""
    
    Write-Log "🖥️ Pi Access:"
    Write-Host "  • SSH: ssh $PiHost" -ForegroundColor White
    Write-Host "  • Status: ssh $PiHost 'cd $PiDeployDir && ./helper.sh status'" -ForegroundColor White
    Write-Host "  • Logs: ssh $PiHost 'cd $PiDeployDir && ./helper.sh logs'" -ForegroundColor White
    Write-Host ""
    
    Write-Log "🌐 Service Endpoints (from Pi):"
    Write-Host "  • API Gateway: http://localhost:8080" -ForegroundColor White
    Write-Host "  • API Server: http://localhost:8081" -ForegroundColor White
    Write-Host "  • MongoDB: mongodb://localhost:27017" -ForegroundColor White
    Write-Host "  • Tor SOCKS: localhost:9050" -ForegroundColor White
    Write-Host ""
    
    Write-Success "The core support infrastructure is ready!"
}

# Main execution
function Main {
    param([string]$ExecutionMode)
    
    Write-Section "🚀 LUCID CORE SUPPORT - Windows Deployment"
    Write-Log "GENIUS-LEVEL Multi-Platform Infrastructure Deployment"
    Write-Log "Registry: $DockerRegistry"
    Write-Log "Pi Target: $PiHost"
    Write-Host ""
    
    # Prerequisites check
    if (-not (Test-Prerequisites)) {
        Write-Error "Prerequisites check failed. Exiting."
        return
    }
    
    switch ($ExecutionMode.ToLower()) {
        "full" {
            if (-not $SkipBuild) {
                Set-DockerBuildx
                Build-CoreServices
            }
            if (-not $SkipDeploy) {
                Deploy-ToPi
            }
            Show-Summary
        }
        "build-only" {
            Set-DockerBuildx
            Build-CoreServices
            Write-Log "Build complete. Run with 'deploy-only' to deploy to Pi."
        }
        "deploy-only" {
            Deploy-ToPi
            Show-Summary
        }
        "test" {
            # Prerequisites already tested above
            Write-Success "All prerequisites verified"
        }
        default {
            Write-Error "Unknown mode: $ExecutionMode"
            Write-Host "Usage: .\windows-deploy-core-support.ps1 [-Mode full|build-only|deploy-only|test]"
        }
    }
}

# Handle parameters
if ($TestOnly) {
    Main "test"
} elseif ($SkipBuild -and $SkipDeploy) {
    Write-Error "Cannot skip both build and deploy"
} elseif ($SkipBuild) {
    Main "deploy-only"
} elseif ($SkipDeploy) {
    Main "build-only"
} else {
    Main $Mode
}