# VS CODE DEVCONTAINER CONNECTION SCRIPT
# Connects VS Code to the running lucid-devcontainer

param(
    [switch]$NewWindow = $false
)

$ContainerName = "lucid-devcontainer-active"

Write-Host "[VS CODE] Connecting to $ContainerName..." -ForegroundColor Green

# Check if container is running
$containerStatus = docker ps --filter "name=$ContainerName" --format "{{.Status}}"

if ([string]::IsNullOrEmpty($containerStatus)) {
    Write-Error "[VS CODE] Container '$ContainerName' is not running!"
    Write-Host "[VS CODE] Starting container first..." -ForegroundColor Yellow
    & ./run-lucid-container.ps1 -Detached
    Start-Sleep -Seconds 3
} else {
    Write-Host "[VS CODE] Container is running: $containerStatus" -ForegroundColor Green
}

# Create temporary devcontainer config for attachment
$tempDevContainer = @{
    "name" = "Lucid DevContainer (Attach)"
    "image" = "lucid-devcontainer:latest" 
    "workspaceFolder" = "/workspaces/Lucid"
    "remoteUser" = "root"
    "customizations" = @{
        "vscode" = @{
            "settings" = @{
                "terminal.integrated.defaultProfile.linux" = "bash"
                "terminal.integrated.cwd" = "/workspaces/Lucid"
                "python.defaultInterpreterPath" = "/usr/bin/python3"
                "docker.dockerPath" = "/usr/bin/docker"
            }
            "extensions" = @(
                "ms-python.python",
                "ms-python.vscode-pylance", 
                "ms-azuretools.vscode-docker",
                "redhat.vscode-yaml",
                "ms-vscode.vscode-json"
            )
        }
    }
    "forwardPorts" = @(2222, 8080, 8081, 9050, 9051)
}

# Create .vscode directory if it doesn't exist
if (!(Test-Path ".vscode")) {
    New-Item -ItemType Directory -Path ".vscode" -Force | Out-Null
}

# Write devcontainer config
$tempDevContainer | ConvertTo-Json -Depth 10 | Out-File -FilePath ".vscode/devcontainer-attach.json" -Encoding UTF8

Write-Host "[VS CODE] Generated attachment configuration" -ForegroundColor Cyan

# Method 1: Try to use VS Code Remote-Containers extension
try {
    if ($NewWindow) {
        Write-Host "[VS CODE] Opening new VS Code window connected to container..." -ForegroundColor Cyan
        code --new-window --remote-container "$ContainerName"
    } else {
        Write-Host "[VS CODE] Connecting current VS Code to container..." -ForegroundColor Cyan  
        code --remote-container "$ContainerName"
    }
    
    Write-Host "[VS CODE] Connection initiated successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 MANUAL CONNECTION STEPS:" -ForegroundColor Yellow
    Write-Host "1. In VS Code, press Ctrl+Shift+P" -ForegroundColor White
    Write-Host "2. Type 'Remote-Containers: Attach to Running Container'" -ForegroundColor White
    Write-Host "3. Select '$ContainerName'" -ForegroundColor White
    Write-Host "4. VS Code will open connected to the Linux environment" -ForegroundColor White
    Write-Host ""
    Write-Host "🔧 CONTAINER ACCESS:" -ForegroundColor Yellow
    Write-Host "Terminal: docker exec -it $ContainerName /bin/bash" -ForegroundColor Cyan
    Write-Host "Working Dir: /workspaces/Lucid" -ForegroundColor Cyan
    Write-Host "Python: /usr/bin/python3" -ForegroundColor Cyan
    
} catch {
    Write-Warning "[VS CODE] Automated connection failed: $_"
    Write-Host ""
    Write-Host "📋 MANUAL CONNECTION:" -ForegroundColor Yellow
    Write-Host "1. Open VS Code" -ForegroundColor White
    Write-Host "2. Install 'Remote - Containers' extension if not installed" -ForegroundColor White  
    Write-Host "3. Press Ctrl+Shift+P" -ForegroundColor White
    Write-Host "4. Type 'Remote-Containers: Attach to Running Container'" -ForegroundColor White
    Write-Host "5. Select '$ContainerName'" -ForegroundColor White
}