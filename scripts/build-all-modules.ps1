# LUCID Complete Module Build Script
# Builds all missing Layer 1 and Layer 2 modules based on SPEC-1 requirements
# Multi-platform build for ARM64 Pi and AMD64 development

param(
    [string]$Registry = "pickme",
    [string]$Repository = "lucid",
    [string]$Tag = "latest",
    [switch]$Push = $true,
    [switch]$NoCache = $true,
    [switch]$Verbose = $false,
    [switch]$Layer1Only = $false,
    [switch]$Layer2Only = $false
)

# Set error handling
$ErrorActionPreference = "Stop"

Write-Host "=== LUCID Complete Module Build ===" -ForegroundColor Green
Write-Host "Registry: $Registry" -ForegroundColor Yellow
Write-Host "Repository: $Repository" -ForegroundColor Yellow
Write-Host "Tag: $Tag" -ForegroundColor Yellow
Write-Host "Push: $Push" -ForegroundColor Yellow
Write-Host "No Cache: $NoCache" -ForegroundColor Yellow
Write-Host "Verbose: $Verbose" -ForegroundColor Yellow
Write-Host "Layer 1 Only: $Layer1Only" -ForegroundColor Yellow
Write-Host "Layer 2 Only: $Layer2Only" -ForegroundColor Yellow
Write-Host ""

# Verify Docker buildx
Write-Host "Verifying Docker buildx..." -ForegroundColor Cyan
try {
    docker buildx version
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker buildx not available" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Docker buildx error: $_" -ForegroundColor Red
    exit 1
}

# Verify Docker Hub login
if ($Push) {
    Write-Host "Verifying Docker Hub login..." -ForegroundColor Cyan
    try {
        docker info | Select-String "Username"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Docker Hub login required" -ForegroundColor Red
            Write-Host "Please run: docker login" -ForegroundColor Yellow
            exit 1
        }
    } catch {
        Write-Host "❌ Docker Hub login error: $_" -ForegroundColor Red
        exit 1
    }
}

# Build configuration
$BuildArgs = @(
    "buildx", "build"
    "--platform", "linux/amd64,linux/arm64"
    "--no-cache"
    "--push"
)

if ($Verbose) {
    $BuildArgs += "--progress=plain"
}

# Layer 1 Modules
$Layer1Modules = @(
    @{
        Name = "Session Recorder"
        Dockerfile = "sessions/recorder/Dockerfile.session-recorder"
        Image = "session-recorder"
        Description = "Session recording with hardware acceleration"
    }
)

# Layer 2 Modules
$Layer2Modules = @(
    @{
        Name = "RDP Server Manager"
        Dockerfile = "RDP/server/Dockerfile.server-manager"
        Image = "rdp-server-manager"
        Description = "RDP server management"
    },
    @{
        Name = "xrdp Integration"
        Dockerfile = "RDP/server/Dockerfile.xrdp-integration"
        Image = "xrdp-integration"
        Description = "xrdp service integration"
    },
    @{
        Name = "Contract Deployment"
        Dockerfile = "blockchain/deployment/Dockerfile.contract-deployment"
        Image = "contract-deployment"
        Description = "Smart contract deployment"
    },
    @{
        Name = "On-System Chain Client"
        Dockerfile = "blockchain/on_system_chain/Dockerfile.chain-client"
        Image = "on-system-chain-client"
        Description = "On-system blockchain client"
    },
    @{
        Name = "TRON Node Client"
        Dockerfile = "blockchain/tron_node/Dockerfile.tron-client"
        Image = "tron-node-client"
        Description = "TRON blockchain client"
    },
    @{
        Name = "Admin UI"
        Dockerfile = "admin/ui/Dockerfile.admin-ui"
        Image = "admin-ui"
        Description = "Admin web interface"
    }
)

# Build Layer 1 modules
if (-not $Layer2Only) {
    Write-Host "=== Building Layer 1 Modules ===" -ForegroundColor Green
    
    foreach ($module in $Layer1Modules) {
        Write-Host "Building $($module.Name)..." -ForegroundColor Cyan
        
        $moduleArgs = $BuildArgs + @(
            "--tag", "${Registry}/${Repository}:$($module.Image)-${Tag}",
            "--tag", "${Registry}/${Repository}:$($module.Image)",
            "--file", $module.Dockerfile,
            "."
        )
        
        try {
            if ($Verbose) {
                Write-Host "Command: docker $($moduleArgs -join ' ')" -ForegroundColor Gray
            }
            
            docker @moduleArgs
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ $($module.Name) built successfully" -ForegroundColor Green
            } else {
                Write-Host "❌ $($module.Name) build failed" -ForegroundColor Red
                exit 1
            }
        } catch {
            Write-Host "❌ $($module.Name) build error: $_" -ForegroundColor Red
            exit 1
        }
    }
}

# Build Layer 2 modules
if (-not $Layer1Only) {
    Write-Host "=== Building Layer 2 Modules ===" -ForegroundColor Green
    
    foreach ($module in $Layer2Modules) {
        Write-Host "Building $($module.Name)..." -ForegroundColor Cyan
        
        $moduleArgs = $BuildArgs + @(
            "--tag", "${Registry}/${Repository}:$($module.Image)-${Tag}",
            "--tag", "${Registry}/${Repository}:$($module.Image)",
            "--file", $module.Dockerfile,
            "."
        )
        
        try {
            if ($Verbose) {
                Write-Host "Command: docker $($moduleArgs -join ' ')" -ForegroundColor Gray
            }
            
            docker @moduleArgs
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ $($module.Name) built successfully" -ForegroundColor Green
            } else {
                Write-Host "❌ $($module.Name) build failed" -ForegroundColor Red
                exit 1
            }
        } catch {
            Write-Host "❌ $($module.Name) build error: $_" -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host ""
Write-Host "=== All Modules Built Successfully ===" -ForegroundColor Green

# Summary
$BuiltModules = @()
if (-not $Layer2Only) {
    $BuiltModules += $Layer1Modules
}
if (-not $Layer1Only) {
    $BuiltModules += $Layer2Modules
}

Write-Host "Built and pushed images:" -ForegroundColor Yellow
foreach ($module in $BuiltModules) {
    Write-Host "  - ${Registry}/${Repository}:$($module.Image)" -ForegroundColor White
}

Write-Host ""
Write-Host "All modules are ready for deployment" -ForegroundColor Green
Write-Host "Use docker-compose to deploy Layer 1 and Layer 2 services" -ForegroundColor Green
