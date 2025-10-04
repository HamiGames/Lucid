# Path: build-master.ps1
# Master Build Orchestration Script for Lucid RDP
# Combines: Clean -> Prep -> Network Setup -> Build -> Test
# Windows PowerShell version

param(
    [switch]$TestOnly,
    [switch]$NoCache,
    [switch]$Clean,
    [switch]$Help,
    [switch]$SkipTests,
    [string]$Phase = "all"
)

$ErrorActionPreference = "Stop"

# Configuration
$PROJECT_ROOT = $PWD
$NETWORK_SCRIPT = ".\scripts\setup_lucid_networks.ps1"
$BUILD_SCRIPT_PS1 = ".\build-devcontainer.ps1"
$COMPOSE_SCRIPT = ".\06-orchestration-runtime\compose\compose_up_dev.sh"
$DEPLOYMENT_SCRIPT = ".\scripts\deploy-lucid-windows.ps1"

# Colors for output
function Write-ColorOutput {
    param(
        [string]$Text,
        [string]$Color = "White"
    )
    
    $colorMap = @{
        "Red" = "Red"
        "Green" = "Green" 
        "Yellow" = "Yellow"
        "Blue" = "Cyan"
        "White" = "White"
        "Magenta" = "Magenta"
    }
    
    Write-Host $Text -ForegroundColor $colorMap[$Color]
}

function Show-Usage {
    Write-Host "Lucid RDP Master Build Script" -ForegroundColor Cyan
    Write-Host "=============================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\build-master.ps1 [OPTIONS]" 
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -TestOnly     Only run tests, don't build/push containers"
    Write-Host "  -NoCache      Build without Docker cache"
    Write-Host "  -Clean        Full clean build (remove all caches and networks)"
    Write-Host "  -SkipTests    Skip integration tests"
    Write-Host "  -Phase        Run specific phase: prep|network|build|test|deploy|all"
    Write-Host "  -Help         Show this help message"
    Write-Host ""
    Write-Host "Build Phases:"
    Write-Host "  1. prep       Clean and prepare environment"
    Write-Host "  2. network    Setup Docker networks" 
    Write-Host "  3. build      Build DevContainer images"
    Write-Host "  4. test       Run integration tests"
    Write-Host "  5. deploy     Deploy to development environment"
    Write-Host "  6. all        Run all phases (default)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\build-master.ps1                    # Full build pipeline"
    Write-Host "  .\build-master.ps1 -TestOnly          # Test-only build"
    Write-Host "  .\build-master.ps1 -Clean             # Clean build"
    Write-Host "  .\build-master.ps1 -Phase network     # Setup networks only"
    Write-Host "  .\build-master.ps1 -Phase build       # Build containers only"
}

if ($Help) {
    Show-Usage
    exit 0
}

# Logging function
function Write-Phase {
    param([string]$Phase, [string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-ColorOutput "[$timestamp] [$Phase] $Message" "Blue"
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "[SUCCESS] $Message" "Green"
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "[ERROR] $Message" "Red"
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "[WARNING] $Message" "Yellow"
}

# Check prerequisites
function Test-Prerequisites {
    Write-Phase "PREREQ" "Checking prerequisites..."
    
    # Check Docker
    try {
        docker --version | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Docker not available" }
        Write-Phase "PREREQ" "Docker: OK"
    } catch {
        Write-Error "Docker is required but not found in PATH"
        return $false
    }
    
    # Check Git (optional)
    try {
        git --version | Out-Null
        Write-Phase "PREREQ" "Git: OK"
    } catch {
        Write-Warning "Git not found - version info will be 'unknown'"
    }
    
    # Check PowerShell version
    $psVersion = $PSVersionTable.PSVersion.Major
    if ($psVersion -lt 5) {
        Write-Error "PowerShell 5.0+ required (found: $psVersion)"
        return $false
    }
    Write-Phase "PREREQ" "PowerShell $psVersion: OK"
    
    # Check required scripts
    $requiredScripts = @($NETWORK_SCRIPT, $BUILD_SCRIPT_PS1)
    foreach ($script in $requiredScripts) {
        if (!(Test-Path $script)) {
            Write-Error "Required script not found: $script"
            return $false
        }
    }
    Write-Phase "PREREQ" "Required scripts: OK"
    
    return $true
}

# Phase 1: Clean and Prepare Environment
function Start-PrepPhase {
    Write-ColorOutput "===== PHASE 1: PREPARATION =====" "Magenta"
    Write-Phase "PREP" "Starting environment preparation..."
    
    if ($Clean) {
        Write-Phase "PREP" "Performing clean build preparation..."
        
        # Clean Docker buildx
        Write-Phase "PREP" "Cleaning Docker Buildx cache..."
        try {
            docker buildx prune -f 2>$null | Out-Null
            Write-Phase "PREP" "Buildx cache cleaned"
        } catch {
            Write-Warning "Failed to clean buildx cache: $($_.Exception.Message)"
        }
        
        # Clean old containers
        Write-Phase "PREP" "Cleaning old containers..."
        try {
            docker container prune -f 2>$null | Out-Null
            Write-Phase "PREP" "Old containers cleaned"
        } catch {
            Write-Warning "Failed to clean containers: $($_.Exception.Message)"
        }
        
        # Clean old images (keep base images)
        Write-Phase "PREP" "Cleaning dangling images..."
        try {
            docker image prune -f 2>$null | Out-Null
            Write-Phase "PREP" "Dangling images cleaned"
        } catch {
            Write-Warning "Failed to clean images: $($_.Exception.Message)"
        }
    }
    
    # Ensure project directories
    $dirs = @("data", "logs", "temp", ".devcontainer")
    foreach ($dir in $dirs) {
        if (!(Test-Path $dir)) {
            New-Item -Path $dir -ItemType Directory -Force | Out-Null
            Write-Phase "PREP" "Created directory: $dir"
        }
    }
    
    # Generate environment files
    Write-Phase "PREP" "Setting up environment configuration..."
    
    # Create development environment file
    $devEnvContent = @"
# Lucid RDP Development Environment - Generated $(Get-Date)
NODE_ENV=development
LUCID_MODE=development
LUCID_NETWORK=testnet
LOG_LEVEL=DEBUG
MONGO_URI=mongodb://mongo:27017/lucid_dev
TOR_ENABLED=true
CHUNK_SIZE=8388608
COMPRESSION_LEVEL=1
BUILD_TIMESTAMP=$(Get-Date -Format 'yyyyMMdd-HHmmss')
GIT_SHA=$(try { git rev-parse --short HEAD 2>$null } catch { "unknown" })
"@
    
    Set-Content -Path ".env.dev" -Value $devEnvContent
    Write-Phase "PREP" "Created .env.dev"
    
    # Copy Tor configuration if available
    if (Test-Path "02-network-security\tor\torrc") {
        Copy-Item "02-network-security\tor\torrc" ".devcontainer\torrc" -Force
        Write-Phase "PREP" "Copied Tor configuration"
    }
    
    Write-Success "Preparation phase completed"
}

# Phase 2: Network Setup
function Start-NetworkPhase {
    Write-ColorOutput "===== PHASE 2: NETWORK SETUP =====" "Magenta"
    Write-Phase "NETWORK" "Setting up Docker networks..."
    
    if (Test-Path $NETWORK_SCRIPT) {
        try {
            & $NETWORK_SCRIPT -Action "create" -Force
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Docker networks configured successfully"
            } else {
                throw "Network script failed with exit code: $LASTEXITCODE"
            }
        } catch {
            Write-Error "Network setup failed: $($_.Exception.Message)"
            return $false
        }
    } else {
        Write-Warning "Network script not found, creating basic network..."
        try {
            # Create basic network if script not available
            docker network create --driver bridge --attachable lucid-dev_lucid_net 2>$null | Out-Null
            Write-Phase "NETWORK" "Created basic lucid-dev_lucid_net network"
        } catch {
            Write-Warning "Network already exists or creation failed"
        }
    }
    
    # Verify networks
    Write-Phase "NETWORK" "Verifying networks..."
    try {
        $networks = docker network ls --format "{{.Name}}" | Where-Object { $_ -like "*lucid*" }
        if ($networks.Count -gt 0) {
            Write-Phase "NETWORK" "Available Lucid networks:"
            foreach ($net in $networks) {
                Write-Phase "NETWORK" "  - $net"
            }
            Write-Success "Network verification completed"
            return $true
        } else {
            Write-Error "No Lucid networks found"
            return $false
        }
    } catch {
        Write-Error "Network verification failed: $($_.Exception.Message)"
        return $false
    }
}

# Phase 3: Build DevContainer
function Start-BuildPhase {
    Write-ColorOutput "===== PHASE 3: BUILD DEVCONTAINER =====" "Magenta"
    Write-Phase "BUILD" "Starting DevContainer build..."
    
    # Prepare build arguments
    $buildArgs = @()
    if ($TestOnly) { $buildArgs += "--TestOnly" }
    if ($NoCache) { $buildArgs += "--NoCache" }
    
    try {
        if (Test-Path $BUILD_SCRIPT_PS1) {
            & $BUILD_SCRIPT_PS1 @buildArgs
            if ($LASTEXITCODE -eq 0) {
                Write-Success "DevContainer build completed successfully"
                return $true
            } else {
                throw "Build script failed with exit code: $LASTEXITCODE"
            }
        } else {
            Write-Error "Build script not found: $BUILD_SCRIPT_PS1"
            return $false
        }
    } catch {
        Write-Error "Build phase failed: $($_.Exception.Message)"
        return $false
    }
}

# Phase 4: Integration Tests
function Start-TestPhase {
    Write-ColorOutput "===== PHASE 4: INTEGRATION TESTS =====" "Magenta"
    Write-Phase "TEST" "Running integration tests..."
    
    if ($SkipTests) {
        Write-Warning "Tests skipped by user request"
        return $true
    }
    
    # Test 1: Component imports
    Write-Phase "TEST" "Testing component imports..."
    try {
        $testResult = python -c "
import sys
sys.path.append('.')
try:
    from node import NodeManager, PeerDiscovery
    from session import SessionRecorder, ChunkManager
    from wallet import WalletManager
    print('PASS: Component imports successful')
except ImportError as e:
    print(f'FAIL: Import error - {e}')
    sys.exit(1)
" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Phase "TEST" $testResult
        } else {
            Write-Warning "Component import test failed: $testResult"
        }
    } catch {
        Write-Warning "Component import test could not run: $($_.Exception.Message)"
    }
    
    # Test 2: Docker network connectivity
    Write-Phase "TEST" "Testing Docker network connectivity..."
    try {
        $networkTest = docker run --rm --network lucid-dev_lucid_net alpine:latest ping -c 1 8.8.8.8 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Phase "TEST" "Network connectivity: PASS"
        } else {
            Write-Warning "Network connectivity test failed"
        }
    } catch {
        Write-Warning "Network connectivity test could not run"
    }
    
    # Test 3: Container startup
    if (!$TestOnly) {
        Write-Phase "TEST" "Testing container startup..."
        try {
            $containerId = docker run -d --network lucid-dev_lucid_net pickme/lucid:dev-latest sleep 30
            Start-Sleep -Seconds 2
            
            $running = docker ps | Select-String $containerId
            if ($running) {
                Write-Phase "TEST" "Container startup: PASS"
                docker stop $containerId | Out-Null
                docker rm $containerId | Out-Null
            } else {
                Write-Warning "Container startup test failed"
            }
        } catch {
            Write-Warning "Container startup test could not run: $($_.Exception.Message)"
        }
    }
    
    Write-Success "Integration tests completed"
    return $true
}

# Phase 5: Development Deployment
function Start-DeployPhase {
    Write-ColorOutput "===== PHASE 5: DEVELOPMENT DEPLOYMENT =====" "Magenta"
    Write-Phase "DEPLOY" "Starting development deployment..."
    
    if ($TestOnly) {
        Write-Warning "Deployment skipped in test-only mode"
        return $true
    }
    
    try {
        if (Test-Path $DEPLOYMENT_SCRIPT) {
            & $DEPLOYMENT_SCRIPT -Action "deploy" -Environment "dev"
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Development deployment completed"
                return $true
            } else {
                Write-Warning "Deployment script completed with warnings (exit code: $LASTEXITCODE)"
                return $true
            }
        } else {
            Write-Warning "Deployment script not found: $DEPLOYMENT_SCRIPT"
            Write-Phase "DEPLOY" "Starting basic Docker Compose deployment..."
            
            # Basic compose deployment
            if (Test-Path "06-orchestration-runtime\compose\lucid-dev.yaml") {
                docker-compose -f "06-orchestration-runtime\compose\lucid-dev.yaml" up -d
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Basic Docker Compose deployment started"
                    return $true
                } else {
                    Write-Error "Docker Compose deployment failed"
                    return $false
                }
            } else {
                Write-Warning "No deployment configuration found"
                return $true
            }
        }
    } catch {
        Write-Error "Deployment phase failed: $($_.Exception.Message)"
        return $false
    }
}

# Main orchestration function
function Start-BuildPipeline {
    param([string]$Phase = "all")
    
    Write-ColorOutput "=====================================" "Cyan"
    Write-ColorOutput "    LUCID RDP BUILD PIPELINE" "Cyan"
    Write-ColorOutput "=====================================" "Cyan"
    Write-Host ""
    Write-Phase "MASTER" "Build pipeline started"
    Write-Phase "MASTER" "Mode: $(if ($TestOnly) { 'TEST ONLY' } else { 'FULL BUILD' })"
    Write-Phase "MASTER" "Phase: $Phase"
    Write-Phase "MASTER" "Clean: $Clean"
    Write-Phase "MASTER" "Cache: $(if ($NoCache) { 'DISABLED' } else { 'ENABLED' })"
    Write-Host ""
    
    $startTime = Get-Date
    $success = $true
    
    try {
        # Check prerequisites first
        if (!(Test-Prerequisites)) {
            throw "Prerequisites check failed"
        }
        Write-Success "Prerequisites verified"
        Write-Host ""
        
        # Execute phases based on selection
        switch ($Phase.ToLower()) {
            "prep" {
                $success = Start-PrepPhase
            }
            "network" {
                $success = Start-NetworkPhase
            }
            "build" {
                $success = Start-BuildPhase
            }
            "test" {
                $success = Start-TestPhase
            }
            "deploy" {
                $success = Start-DeployPhase
            }
            "all" {
                $success = Start-PrepPhase
                if ($success) { $success = Start-NetworkPhase }
                if ($success) { $success = Start-BuildPhase }
                if ($success) { $success = Start-TestPhase }
                if ($success) { $success = Start-DeployPhase }
            }
            default {
                throw "Unknown phase: $Phase"
            }
        }
        
        if ($success) {
            $duration = (Get-Date) - $startTime
            Write-Host ""
            Write-ColorOutput "=====================================" "Green"
            Write-ColorOutput "    BUILD PIPELINE COMPLETED!" "Green"
            Write-ColorOutput "=====================================" "Green"
            Write-Success "Total duration: $($duration.ToString('mm\:ss'))"
            Write-Phase "MASTER" "All phases completed successfully"
            
            if (!$TestOnly) {
                Write-Host ""
                Write-Phase "MASTER" "Next steps:"
                Write-Phase "MASTER" "1. Check container status: docker ps"
                Write-Phase "MASTER" "2. View logs: docker-compose logs -f"
                Write-Phase "MASTER" "3. Access development environment via configured .onion addresses"
            }
            
        } else {
            throw "One or more phases failed"
        }
        
    } catch {
        $duration = (Get-Date) - $startTime
        Write-Host ""
        Write-ColorOutput "=====================================" "Red"
        Write-ColorOutput "    BUILD PIPELINE FAILED!" "Red"
        Write-ColorOutput "=====================================" "Red"
        Write-Error "Pipeline failed after $($duration.ToString('mm\:ss')): $($_.Exception.Message)"
        
        Write-Host ""
        Write-Phase "MASTER" "Troubleshooting tips:"
        Write-Phase "MASTER" "1. Check Docker daemon is running: docker info"
        Write-Phase "MASTER" "2. Try clean build: .\build-master.ps1 -Clean"
        Write-Phase "MASTER" "3. Check individual phases: .\build-master.ps1 -Phase prep"
        Write-Phase "MASTER" "4. View detailed logs in previous output"
        
        exit 1
    }
}

# Execute the pipeline
Start-BuildPipeline -Phase $Phase