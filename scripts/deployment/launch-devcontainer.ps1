# Launch VS Code with Lucid DevContainer
# This script ensures VS Code connects to the correct container

Write-Host "Starting Lucid DevContainer VS Code Session..." -ForegroundColor Green

# Ensure container is running
$containerStatus = docker ps --filter "name=lucid-devcontainer" --format "{{.Status}}"
if (-not $containerStatus) {
    Write-Host "Starting lucid-devcontainer..." -ForegroundColor Yellow
    docker start lucid-devcontainer
    Start-Sleep 5
}

# Get container ID
$containerId = docker ps --filter "name=lucid-devcontainer" --format "{{.ID}}"
Write-Host "Container ID: $containerId" -ForegroundColor Cyan

# Launch VS Code from current directory first
Write-Host "Launching VS Code..." -ForegroundColor Yellow
code .

Write-Host @"

=== VS Code Launch Instructions ===
1. VS Code will open shortly
2. Press Ctrl+Shift+P to open Command Palette
3. Type: "Dev Containers: Reopen in Container"
4. Select the lucid-devcontainer option

Your devcontainer is ready at: /workspaces/Lucid
Container: lucid-devcontainer ($containerId)

"@ -ForegroundColor Green