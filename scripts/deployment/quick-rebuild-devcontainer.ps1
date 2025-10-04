# LUCID-DEVCONTAINER QUICK REBUILD SCRIPT
# Fast rebuild for existing running devcontainer
# LUCID-STRICT mode compliant
# Version: 1.0.0

param(
    [switch]$Force,
    [switch]$Help
)

$Config = @{
    ImageName = "pickme/lucid"
    DevImageTag = "devcontainer-dind"
    ContainerName = "lucid-devcontainer"
    DockerfilePath = "infrastructure/containers/.devcontainer/Dockerfile"
    ContextPath = "."
}

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    $colors = @{ "Info" = "Cyan"; "Success" = "Green"; "Warning" = "Yellow"; "Error" = "Red" }
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor Gray
    Write-Host $Message -ForegroundColor $colors[$Type]
}

if ($Help) {
    Write-Host @"
LUCID-DEVCONTAINER QUICK REBUILD
=================================

Usage: .\quick-rebuild-devcontainer.ps1 [OPTIONS]

OPTIONS:
  -Force    Force rebuild even if container is healthy
  -Help     Show this help message

This script performs a quick rebuild of the existing lucid-devcontainer.
"@
    exit 0
}

Write-Status "LUCID-DEVCONTAINER QUICK REBUILD STARTING" "Info"
Write-Status "=========================================" "Info"

# Check if container exists and is running
$containerStatus = docker ps --filter "name=$($Config.ContainerName)" --format "{{.Status}}"
if (-not $containerStatus) {
    Write-Status "Container $($Config.ContainerName) is not running. Use full rebuild script instead." "Error"
    exit 1
}

Write-Status "[+] Container $($Config.ContainerName) is running: $containerStatus" "Success"

# Generate new timestamp for quick rebuild
$buildTimestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$gitHash = try { (git rev-parse --short HEAD 2>$null) } catch { "unknown" }

# Quick rebuild with minimal downtime
Write-Status "Performing quick rebuild..." "Info"

# Build new image
$newTag = "$($Config.ImageName):devcontainer-quick-$buildTimestamp"
docker buildx build `
    --file $Config.DockerfilePath `
    --tag $newTag `
    --tag "$($Config.ImageName):$($Config.DevImageTag)" `
    --load `
    --build-arg "BUILDKIT_INLINE_CACHE=1" `
    --build-arg "BUILD_DATE=$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')" `
    --build-arg "GIT_HASH=$gitHash" `
    $Config.ContextPath

if ($LASTEXITCODE -eq 0) {
    Write-Status "[+] Quick rebuild completed successfully" "Success"
    Write-Status "New image: $newTag" "Success"
    
    # Push to registry
    Write-Status "Pushing to registry..." "Info"
    docker push "$($Config.ImageName):$($Config.DevImageTag)"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Status "[+] Image pushed to registry" "Success"
    } else {
        Write-Status "[!] Push failed, but local rebuild succeeded" "Warning"
    }
    
    Write-Status "Quick rebuild completed! Container will use new image on next restart." "Success"
} else {
    Write-Status "[-] Quick rebuild failed" "Error"
    exit 1
}