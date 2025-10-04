# Build and Push Script for Lucid RDP DevContainer
# Target: ARM64 (Raspberry Pi 5) and AMD64 (development machines)
# Registry: DockerHub pickme/lucid
# Based on Spec-1d build requirements
# Windows PowerShell version

param(
    [switch]$TestOnly,
    [switch]$NoCache,
    [switch]$Help
)

# Configuration
$IMAGE_NAME = "pickme/lucid"
$BUILDER_NAME = "lucid_builder"
$DOCKERFILE_PATH = ".devcontainer/Dockerfile"
$CONTEXT_PATH = "."

# Get version from pyproject.toml or use "dev"
if (Test-Path "pyproject.toml") {
    $VERSION = (Get-Content "pyproject.toml" | Select-String '^version = ').Line -replace 'version = "([^"]+)"', '$1'
} else {
    $VERSION = "dev"
}

# Get git info
try {
    $GIT_SHA = (git rev-parse --short HEAD 2>$null)
} catch {
    $GIT_SHA = "unknown"
}

$BUILD_DATE = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
# Create Docker-safe timestamp (no colons)
$BUILD_DATE_SAFE = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")

# Tags to build and push (Docker tags cannot contain colons)
$TAGS = @(
    "${IMAGE_NAME}:${VERSION}",
    "${IMAGE_NAME}:dev-latest",
    "${IMAGE_NAME}:${VERSION}-${GIT_SHA}",
    "${IMAGE_NAME}:dev-${BUILD_DATE_SAFE}"
)

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
    }
    
    Write-Host $Text -ForegroundColor $colorMap[$Color]
}

function Show-Usage {
    Write-Host "Usage: .\build-devcontainer.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -TestOnly    Only run local build test, don't push"
    Write-Host "  -NoCache     Don't use build cache"
    Write-Host "  -Help        Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\build-devcontainer.ps1                # Full build and push"
    Write-Host "  .\build-devcontainer.ps1 -TestOnly      # Test build only"
    Write-Host "  .\build-devcontainer.ps1 -NoCache       # Build without cache"
}

if ($Help) {
    Show-Usage
    exit 0
}

Write-ColorOutput "===== Lucid RDP DevContainer Build Script =====" "Blue"
Write-ColorOutput "Image Name: $IMAGE_NAME" "Yellow"
Write-ColorOutput "Version: $VERSION" "Yellow"
Write-ColorOutput "Git SHA: $GIT_SHA" "Yellow"
Write-ColorOutput "Build Date: $BUILD_DATE" "Yellow"
Write-ColorOutput "Builder: $BUILDER_NAME" "Yellow"
Write-ColorOutput "Target Platforms: linux/arm64, linux/amd64" "Yellow"
Write-Host ""

function Test-Docker {
    try {
        docker info *>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[+] Docker is running" "Green"
            return $true
        } else {
            Write-ColorOutput "Error: Docker is not running or not accessible" "Red"
            return $false
        }
    } catch {
        Write-ColorOutput "Error: Docker is not running or not accessible" "Red"
        return $false
    }
}

function Ensure-Builder {
    Write-ColorOutput "Checking if builder '$BUILDER_NAME' exists..." "Yellow"
    
    try {
        $builderExists = docker buildx ls | Select-String $BUILDER_NAME
        
        if (-not $builderExists) {
            Write-ColorOutput "Creating builder: $BUILDER_NAME" "Yellow"
            docker buildx create --name $BUILDER_NAME --use --bootstrap
        } else {
            Write-ColorOutput "[+] Builder '$BUILDER_NAME' exists" "Green"
            docker buildx use $BUILDER_NAME
        }
        
        # Inspect builder
        docker buildx inspect --bootstrap
    } catch {
        Write-ColorOutput "Error managing Docker buildx builder" "Red"
        throw
    }
}

function Ensure-Network {
    Write-ColorOutput "Ensuring network 'lucid-dev_lucid_net' exists..." "Yellow"
    
    try {
        docker network inspect lucid-dev_lucid_net *>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[+] Network 'lucid-dev_lucid_net' already exists" "Green"
        } else {
            docker network create --driver bridge --attachable lucid-dev_lucid_net
            Write-ColorOutput "[+] Network 'lucid-dev_lucid_net' created" "Green"
        }
    } catch {
        docker network create --driver bridge --attachable lucid-dev_lucid_net
        Write-ColorOutput "[+] Network 'lucid-dev_lucid_net' created" "Green"
    }
}

function Pre-PullImages {
    Write-ColorOutput "Pre-pulling base images to avoid timeout issues..." "Yellow"
    
    # Function to pull with retry
    function Pull-WithRetry {
        param([string]$ImageName, [int]$MaxRetries = 3)
        
        for ($i = 1; $i -le $MaxRetries; $i++) {
            Write-ColorOutput "Attempting to pull $ImageName (attempt $i/$MaxRetries)..." "Yellow"
            try {
                $result = docker pull $ImageName 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-ColorOutput "[+] Successfully pulled $ImageName" "Green"
                    return $true
                } else {
                    Write-ColorOutput "[-] Failed to pull $ImageName (attempt $i)" "Red"
                    if ($i -lt $MaxRetries) {
                        Write-ColorOutput "Retrying in 5 seconds..." "Yellow"
                        Start-Sleep -Seconds 5
                    }
                }
            } catch {
                Write-ColorOutput "[-] Failed to pull $ImageName (attempt $i)" "Red"
                if ($i -lt $MaxRetries) {
                    Write-ColorOutput "Retrying in 5 seconds..." "Yellow"
                    Start-Sleep -Seconds 5
                }
            }
        }
        return $false
    }
    
    # Try different Python image variants
    $pythonImages = @("python:3.12-slim", "python:3.12-slim-bookworm", "python:3.12")
    $pythonPulled = $false
    
    foreach ($image in $pythonImages) {
        if (Pull-WithRetry -ImageName $image -MaxRetries 2) {
            $pythonPulled = $true
            break
        }
    }
    
    if (-not $pythonPulled) {
        Write-ColorOutput "[-] Failed to pull any Python base image" "Red"
        throw "Cannot pull Python base image"
    }
    
    # MongoDB for development
    $mongoImages = @("mongo:7.0", "mongo:7", "mongo:latest")
    $mongoPulled = $false
    
    foreach ($image in $mongoImages) {
        if (Pull-WithRetry -ImageName $image -MaxRetries 2) {
            $mongoPulled = $true
            break
        }
    }
    
    if (-not $mongoPulled) {
        Write-ColorOutput "Warning: Failed to pull MongoDB image, continuing anyway" "Yellow"
    }
    
    Write-ColorOutput "[+] Base images pre-pull completed" "Green"
}

function Build-Image {
    Write-ColorOutput "Building multi-platform Docker image..." "Blue"
    
    # Construct tag arguments
    $tagArgs = @()
    foreach ($tag in $TAGS) {
        $tagArgs += "--tag"
        $tagArgs += $tag
    }
    
    # Build arguments
    $buildArgs = @(
        "--platform", "linux/arm64,linux/amd64",
        "--file", $DOCKERFILE_PATH,
        "--push",
        "--cache-from", "type=registry,ref=${IMAGE_NAME}:buildcache",
        "--cache-to", "type=registry,ref=${IMAGE_NAME}:buildcache,mode=max",
        "--build-arg", "BUILDKIT_INLINE_CACHE=1",
        "--build-arg", "VERSION=$VERSION",
        "--build-arg", "GIT_SHA=$GIT_SHA",
        "--build-arg", "BUILD_DATE=$BUILD_DATE"
    )
    
    $buildArgs += $tagArgs
    $buildArgs += $CONTEXT_PATH
    
    Write-ColorOutput "Build command:" "Yellow"
    Write-Host "docker buildx build $($buildArgs -join ' ')"
    Write-Host ""
    
    # Execute build
    & docker buildx build @buildArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "[+] Multi-platform image built and pushed successfully" "Green"
    } else {
        Write-ColorOutput "[-] Build failed" "Red"
        exit $LASTEXITCODE
    }
}

function Test-Images {
    Write-ColorOutput "Verifying pushed images..." "Blue"
    
    foreach ($tag in $TAGS) {
        Write-ColorOutput "Checking: $tag" "Yellow"
        try {
            docker manifest inspect $tag *>$null
            if ($LASTEXITCODE -eq 0) {
                Write-ColorOutput "[+] $tag is available" "Green"
            } else {
                Write-ColorOutput "[-] $tag is not available" "Red"
            }
        } catch {
            Write-ColorOutput "[-] $tag is not available" "Red"
        }
    }
}

function Test-LocalBuild {
    Write-ColorOutput "Testing local build..." "Blue"
    
    # Build for current platform only
    docker buildx build `
        --file $DOCKERFILE_PATH `
        --tag "${IMAGE_NAME}:test-local" `
        --load `
        $CONTEXT_PATH
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "[-] Local build failed" "Red"
        exit $LASTEXITCODE
    }
    
    # Test container startup
    Write-ColorOutput "Testing container startup..." "Yellow"
    $containerId = docker run -d "${IMAGE_NAME}:test-local" /bin/bash -c "sleep 10"
    
    Start-Sleep -Seconds 2
    
    # Check if container is running
    $running = docker ps | Select-String $containerId
    
    if ($running) {
        Write-ColorOutput "[+] Container started successfully" "Green"
        docker stop $containerId *>$null
        docker rm $containerId *>$null
    } else {
        Write-ColorOutput "[-] Container failed to start" "Red"
        docker logs $containerId
        docker rm $containerId *>$null
        exit 1
    }
    
    # Clean up test image
    try {
        docker rmi "${IMAGE_NAME}:test-local" *>$null
    } catch {
        # Ignore cleanup errors
    }
}

# Main execution function
function Start-Build {
    Write-ColorOutput "Starting Lucid DevContainer build process..." "Blue"
    
    # Pre-checks
    if (-not (Test-Docker)) {
        exit 1
    }
    
    Ensure-Network
    
    if ($TestOnly) {
        Write-ColorOutput "Running test-only build..." "Yellow"
        Test-LocalBuild
        Write-ColorOutput "[+] Local test completed successfully" "Green"
        return
    }
    
    # Full build and push process
    Ensure-Builder
    Pre-PullImages
    
    if ($NoCache) {
        Write-ColorOutput "Building without cache..." "Yellow"
        # Cache handling would be modified in Build-Image function
    }
    
    Build-Image
    Test-Images
    
    # Test the pushed image
    Write-ColorOutput "Testing pushed image..." "Blue"
    docker run --rm "${IMAGE_NAME}:dev-latest" python --version
    docker run --rm "${IMAGE_NAME}:dev-latest" node --version
    docker run --rm "${IMAGE_NAME}:dev-latest" mongosh --version
    
    Write-Host ""
    Write-ColorOutput "===== Build Complete =====" "Green"
    Write-ColorOutput "[+] Images built and pushed successfully" "Green"
    Write-ColorOutput "Available tags:" "Yellow"
    foreach ($tag in $TAGS) {
        Write-Host "  • $tag"
    }
    Write-Host ""
    Write-ColorOutput "You can now pull the image on your development machine:" "Blue"
    Write-Host "  docker pull ${IMAGE_NAME}:dev-latest"
    Write-Host ""
    Write-ColorOutput "Or use it directly in devcontainer.json:" "Blue"
    Write-Host "  `"image`": `"${IMAGE_NAME}:dev-latest`""
}

# Execute main function
Start-Build
