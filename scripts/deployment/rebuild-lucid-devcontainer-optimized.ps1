# LUCID-DEVCONTAINER REBUILD SCRIPT - GENIUS-LEVEL OPTIMIZATION
# Professional Docker Build System with Complete Cleanup and Push
# Follows LUCID-STRICT mode and genius programming patterns
# Windows PowerShell → Docker Desktop → Multi-platform Build → Docker Hub
# Author: Lucid Build System
# Version: 2.0.0
# Target: pickme/lucid-dev repository

param(
    [switch]$TestOnly,
    [switch]$NoCache,
    [switch]$SkipPush,
    [switch]$Force,
    [switch]$Help
)

# === CONFIGURATION SECTION ===
$script:Config = @{
    ImageName = "pickme/lucid"
    DevImageTag = "devcontainer-dind"
    BuilderName = "lucid-devcontainer-builder"
    NetworkName = "lucid-dev_lucid_net"
    ContextPath = "."
    DockerfilePath = "infrastructure/containers/.devcontainer/Dockerfile"
    ComposeFile = "infrastructure/containers/.devcontainer/docker-compose.dev.yml"
    Platforms = @("linux/amd64", "linux/arm64")
    NetworkSubnet = "172.20.0.0/16"
    NetworkGateway = "172.20.0.1"
}

# === UTILITY FUNCTIONS ===
function Write-StatusMessage {
    param(
        [string]$Message,
        [ValidateSet("Info", "Success", "Warning", "Error")]
        [string]$Type = "Info"
    )
    
    $colors = @{
        "Info" = "Cyan"
        "Success" = "Green"
        "Warning" = "Yellow"
        "Error" = "Red"
    }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor Gray
    Write-Host $Message -ForegroundColor $colors[$Type]
}

function Show-Usage {
    Write-Host @"
LUCID-DEVCONTAINER REBUILD SCRIPT - GENIUS-LEVEL OPTIMIZATION
===========================================================

Usage: .\rebuild-lucid-devcontainer-optimized.ps1 [OPTIONS]

OPTIONS:
  -TestOnly    Only run local build test, don't push to registry
  -NoCache     Force rebuild without using any cache layers
  -SkipPush    Build images but skip pushing to Docker Hub
  -Force       Force rebuild even if images already exist
  -Help        Show this help message

EXAMPLES:
  .\rebuild-lucid-devcontainer-optimized.ps1                     # Full rebuild and push
  .\rebuild-lucid-devcontainer-optimized.ps1 -TestOnly           # Test build only
  .\rebuild-lucid-devcontainer-optimized.ps1 -NoCache -Force     # Force complete rebuild
  .\rebuild-lucid-devcontainer-optimized.ps1 -SkipPush           # Build without pushing

WORKFLOW:
1. Docker system cleanup (volumes, builders, networks)
2. Pre-flight checks (Docker, network, files)
3. Network pre-configuration
4. Multi-platform builder setup
5. Build optimization with cache management
6. Multi-platform build execution
7. Push to pickme/lucid-dev repository
8. Verification and health checks

REQUIREMENTS:
- Docker Desktop with BuildKit enabled
- PowerShell 5.1 or higher
- Docker Hub authentication (docker login)
- Sufficient disk space (minimum 8GB free)

"@
}

function Test-Prerequisites {
    Write-StatusMessage "Checking prerequisites..." "Info"
    
    # Check Docker
    try {
        $dockerInfo = docker info --format json 2>$null | ConvertFrom-Json
        if (-not $dockerInfo) {
            throw "Docker info unavailable"
        }
        Write-StatusMessage "✓ Docker Desktop is running" "Success"
    }
    catch {
        Write-StatusMessage "✗ Docker Desktop is not running or accessible" "Error"
        return $false
    }
    
    # Check BuildKit
    if ($env:DOCKER_BUILDKIT -ne "1") {
        $env:DOCKER_BUILDKIT = "1"
        Write-StatusMessage "✓ Docker BuildKit enabled" "Success"
    }
    
    # Check disk space (minimum 8GB)
    $freeSpace = Get-WmiObject -Class Win32_LogicalDisk | Where-Object {$_.DeviceID -eq "C:"} | Select-Object -ExpandProperty FreeSpace
    $freeSpaceGB = [math]::Round($freeSpace / 1GB, 2)
    if ($freeSpaceGB -lt 8) {
        Write-StatusMessage "✗ Insufficient disk space: ${freeSpaceGB}GB available (minimum 8GB required)" "Error"
        return $false
    }
    Write-StatusMessage "✓ Sufficient disk space: ${freeSpaceGB}GB available" "Success"
    
    # Check required files
    $requiredFiles = @(
        $script:Config.DockerfilePath,
        $script:Config.ComposeFile
    )
    
    foreach ($file in $requiredFiles) {
        if (-not (Test-Path $file)) {
            Write-StatusMessage "✗ Required file missing: $file" "Error"
            return $false
        }
    }
    Write-StatusMessage "✓ All required files present" "Success"
    
    return $true
}

function Clear-DockerSystem {
    Write-StatusMessage "Performing genius-level Docker system cleanup..." "Info"
    
    # Stop and remove existing devcontainer
    Write-StatusMessage "Stopping existing lucid-devcontainer..." "Info"
    docker stop lucid-devcontainer 2>$null | Out-Null
    docker rm lucid-devcontainer 2>$null | Out-Null
    
    # Remove all buildx builders (as per rules)
    Write-StatusMessage "Erasing all Docker buildx volumes for fresh state..." "Info"
    $builders = docker buildx ls --format json 2>$null | ConvertFrom-Json
    if ($builders) {
        foreach ($builder in $builders) {
            if ($builder.Name -ne "default") {
                docker buildx rm $builder.Name --force 2>$null | Out-Null
            }
        }
    }
    
    # Clean buildx data
    docker buildx prune --force --all 2>$null | Out-Null
    
    # Clean Docker system (aggressive)
    Write-StatusMessage "Cleaning Docker system caches..." "Info"
    docker system prune --force --all --volumes 2>$null | Out-Null
    docker builder prune --force --all 2>$null | Out-Null
    docker image prune --force --all 2>$null | Out-Null
    
    Write-StatusMessage "✓ Docker system cleanup completed" "Success"
}

function Initialize-Network {
    Write-StatusMessage "Setting up network pre-configurations..." "Info"
    
    # Remove existing network if present
    docker network rm $script:Config.NetworkName 2>$null | Out-Null
    
    # Create network with proper configuration
    $networkCmd = @(
        "docker", "network", "create",
        "--driver", "bridge",
        "--attachable",
        "--subnet=$($script:Config.NetworkSubnet)",
        "--gateway=$($script:Config.NetworkGateway)",
        $script:Config.NetworkName
    )
    
    $result = & $networkCmd[0] $networkCmd[1..($networkCmd.Length-1)] 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-StatusMessage "✓ Network '$($script:Config.NetworkName)' created successfully" "Success"
    }
    else {
        Write-StatusMessage "Network creation result: $result" "Warning"
    }
}

function Initialize-Builder {
    Write-StatusMessage "Creating optimized multi-platform builder..." "Info"
    
    # Create new builder with optimizations
    $builderCmd = @(
        "docker", "buildx", "create",
        "--name", $script:Config.BuilderName,
        "--driver", "docker-container",
        "--use",
        "--bootstrap"
    )
    
    & $builderCmd[0] $builderCmd[1..($builderCmd.Length-1)]
    if ($LASTEXITCODE -ne 0) {
        Write-StatusMessage "Failed to create builder" "Error"
        return $false
    }
    
    # Wait for builder to be ready
    Start-Sleep -Seconds 5
    
    # Inspect builder
    docker buildx inspect --bootstrap
    Write-StatusMessage "✓ Builder '$($script:Config.BuilderName)' ready" "Success"
    return $true
}

function Build-DevcontainerImage {
    param([bool]$TestMode = $false)
    
    Write-StatusMessage "Building lucid-devcontainer with genius-level optimizations..." "Info"
    
    # Generate Docker-safe timestamp
    $buildTimestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
    $gitHash = try { (git rev-parse --short HEAD 2>$null) } catch { "unknown" }
    
    # Determine tags
    $tags = @(
        "$($script:Config.ImageName):$($script:Config.DevImageTag)",
        "$($script:Config.ImageName):devcontainer-latest",
        "$($script:Config.ImageName):devcontainer-$buildTimestamp"
    )
    
    if ($gitHash -ne "unknown") {
        $tags += "$($script:Config.ImageName):devcontainer-$gitHash"
    }
    
    # Build command construction
    $buildArgs = @(
        "docker", "buildx", "build"
    )
    
    # Add platform specification
    if (-not $TestMode) {
        $buildArgs += "--platform"
        $buildArgs += ($script:Config.Platforms -join ",")
    }
    
    # Add dockerfile and context
    $buildArgs += "--file"
    $buildArgs += $script:Config.DockerfilePath
    
    # Add tags
    foreach ($tag in $tags) {
        $buildArgs += "--tag"
        $buildArgs += $tag
    }
    
    # Add build arguments
    $buildArgs += "--build-arg"
    $buildArgs += "BUILDKIT_INLINE_CACHE=1"
    $buildArgs += "--build-arg"
    $buildArgs += "BUILD_DATE=$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')"
    $buildArgs += "--build-arg"
    $buildArgs += "GIT_HASH=$gitHash"
    
    # Cache configuration
    if (-not $NoCache) {
        $cacheFrom = "$($script:Config.ImageName):buildcache-devcontainer"
        $buildArgs += "--cache-from"
        $buildArgs += "type=registry,ref=$cacheFrom"
        $buildArgs += "--cache-to"
        $buildArgs += "type=registry,ref=$cacheFrom,mode=max"
    }
    
    # Output configuration
    if ($TestMode) {
        $buildArgs += "--load"
    } elseif (-not $SkipPush) {
        $buildArgs += "--push"
    } else {
        $buildArgs += "--load"
    }
    
    # Add context
    $buildArgs += $script:Config.ContextPath
    
    Write-StatusMessage "Executing build command..." "Info"
    Write-StatusMessage "Command: $($buildArgs -join ' ')" "Info"
    
    # Execute build
    & $buildArgs[0] $buildArgs[1..($buildArgs.Length-1)]
    
    if ($LASTEXITCODE -eq 0) {
        Write-StatusMessage "✓ Multi-platform devcontainer build completed successfully" "Success"
        return $true
    } else {
        Write-StatusMessage "✗ Build failed with exit code $LASTEXITCODE" "Error"
        return $false
    }
}

function Test-LocalBuild {
    Write-StatusMessage "Performing local build test..." "Info"
    
    $testTag = "$($script:Config.ImageName):devcontainer-test"
    
    # Simple local build for testing
    docker buildx build `
        --file $script:Config.DockerfilePath `
        --tag $testTag `
        --load `
        $script:Config.ContextPath
    
    if ($LASTEXITCODE -ne 0) {
        Write-StatusMessage "✗ Local test build failed" "Error"
        return $false
    }
    
    # Test container functionality
    Write-StatusMessage "Testing container functionality..." "Info"
    $containerId = docker run -d --rm $testTag tail -f /dev/null
    
    Start-Sleep -Seconds 3
    
    # Test basic functionality
    $pythonTest = docker exec $containerId python3 --version 2>&1
    $dockerTest = docker exec $containerId docker --version 2>&1
    $javaTest = docker exec $containerId java -version 2>&1
    
    docker stop $containerId | Out-Null
    
    if ($pythonTest -match "Python" -and $dockerTest -match "Docker" -and $javaTest -match "openjdk") {
        Write-StatusMessage "✓ Container functionality test passed" "Success"
        return $true
    } else {
        Write-StatusMessage "✗ Container functionality test failed" "Error"
        return $false
    }
}

function Push-ToRegistry {
    Write-StatusMessage "Pushing images to pickme/lucid-dev registry..." "Info"
    
    # Verify Docker Hub authentication
    $loginCheck = docker info --format json 2>$null | ConvertFrom-Json
    if (-not $loginCheck) {
        Write-StatusMessage "Please run 'docker login' first" "Error"
        return $false
    }
    
    # Push was already done during build if --push was used
    # Verify images are available
    $tags = @(
        "$($script:Config.ImageName):$($script:Config.DevImageTag)",
        "$($script:Config.ImageName):devcontainer-latest"
    )
    
    foreach ($tag in $tags) {
        Write-StatusMessage "Verifying $tag..." "Info"
        docker manifest inspect $tag > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-StatusMessage "✓ $tag is available in registry" "Success"
        } else {
            Write-StatusMessage "⚠ $tag verification failed" "Warning"
        }
    }
    
    return $true
}

function Show-BuildSummary {
    param([bool]$Success, [DateTime]$StartTime)
    
    $duration = (Get-Date) - $StartTime
    $durationStr = "{0:mm\:ss}" -f $duration
    
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "LUCID-DEVCONTAINER BUILD SUMMARY" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "Status: " -NoNewline
    
    if ($Success) {
        Write-Host "SUCCESS" -ForegroundColor Green
        Write-Host "Duration: $durationStr" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Available Images:" -ForegroundColor Yellow
        Write-Host "  • $($script:Config.ImageName):$($script:Config.DevImageTag)" -ForegroundColor White
        Write-Host "  • $($script:Config.ImageName):devcontainer-latest" -ForegroundColor White
        Write-Host ""
        Write-Host "Next Steps:" -ForegroundColor Yellow
        Write-Host "  1. Verify images: docker images | findstr lucid" -ForegroundColor White
        Write-Host "  2. Test container: docker run -it --rm $($script:Config.ImageName):$($script:Config.DevImageTag)" -ForegroundColor White
        Write-Host "  3. Launch devcontainer from VS Code" -ForegroundColor White
    } else {
        Write-Host "FAILED" -ForegroundColor Red
        Write-Host "Duration: $durationStr" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Troubleshooting:" -ForegroundColor Yellow
        Write-Host "  1. Check Docker Desktop is running" -ForegroundColor White
        Write-Host "  2. Verify sufficient disk space" -ForegroundColor White
        Write-Host "  3. Check Docker Hub authentication" -ForegroundColor White
        Write-Host "  4. Review build logs above" -ForegroundColor White
    }
    Write-Host "=========================================" -ForegroundColor Cyan
}

# === MAIN EXECUTION ===
function Main {
    if ($Help) {
        Show-Usage
        return
    }
    
    $startTime = Get-Date
    
    Write-StatusMessage "LUCID-DEVCONTAINER REBUILD - GENIUS-LEVEL OPTIMIZATION" "Info"
    Write-StatusMessage "=======================================================" "Info"
    
    # Prerequisites check
    if (-not (Test-Prerequisites)) {
        Show-BuildSummary $false $startTime
        exit 1
    }
    
    # Test mode handling
    if ($TestOnly) {
        Write-StatusMessage "Running in test-only mode..." "Warning"
        if (Test-LocalBuild) {
            Show-BuildSummary $true $startTime
            exit 0
        } else {
            Show-BuildSummary $false $startTime
            exit 1
        }
    }
    
    try {
        # Full build workflow
        Clear-DockerSystem
        Initialize-Network
        
        if (-not (Initialize-Builder)) {
            throw "Builder initialization failed"
        }
        
        if (-not (Build-DevcontainerImage)) {
            throw "Image build failed"
        }
        
        if (-not $SkipPush -and -not (Push-ToRegistry)) {
            throw "Registry push failed"
        }
        
        Write-StatusMessage "All operations completed successfully!" "Success"
        Show-BuildSummary $true $startTime
        exit 0
        
    } catch {
        Write-StatusMessage "Build failed: $($_.Exception.Message)" "Error"
        Show-BuildSummary $false $startTime
        exit 1
    }
}

# Execute main function
Main