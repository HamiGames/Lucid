# Build Beta Sidecar Container - AMD64
# LUCID RDP - Stage 0: Beta Sidecar

param(
    [string]$Version = "0.1.0",
    [switch]$Push = $false,
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

$BUILD_DATE = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ' -AsUTC)
$IMAGE_NAME = "pickme/lucid-beta"
$DOCKERFILE = "docker/Dockerfile.beta"

Write-Host "Building LUCID Beta Sidecar v$Version" -ForegroundColor Green
Write-Host "Platform: linux/amd64" -ForegroundColor Yellow
Write-Host "Build Date: $BUILD_DATE" -ForegroundColor Yellow

# Verify Dockerfile exists
if (-not (Test-Path $DOCKERFILE)) {
    Write-Error "Dockerfile not found: $DOCKERFILE"
    exit 1
}

# Build command
$buildArgs = @(
    "build"
    "--platform", "linux/amd64"
    "--file", $DOCKERFILE
    "--tag", "${IMAGE_NAME}:${Version}"
    "--tag", "${IMAGE_NAME}:latest"
    "--build-arg", "VERSION=$Version"
    "--build-arg", "BUILD_DATE=$BUILD_DATE"
)

if ($Verbose) {
    $buildArgs += "--progress=plain"
}

$buildArgs += "."

Write-Host "Running: docker $($buildArgs -join ' ')" -ForegroundColor Cyan

docker @buildArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "`nBuild successful!" -ForegroundColor Green
Write-Host "Images tagged:"
Write-Host "  - ${IMAGE_NAME}:${Version}" -ForegroundColor Blue
Write-Host "  - ${IMAGE_NAME}:latest" -ForegroundColor Blue

if ($Push) {
    Write-Host "`nPushing images..." -ForegroundColor Yellow
    docker push "${IMAGE_NAME}:${Version}"
    docker push "${IMAGE_NAME}:latest"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Push successful!" -ForegroundColor Green
    } else {
        Write-Error "Push failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

Write-Host "`nTo test the container:" -ForegroundColor Cyan
Write-Host "docker run --rm -it ${IMAGE_NAME}:${Version} /bin/bash"