# PowerShell script to pull the Docker image and launch VS Code with the Lucid DevContainer
# Run this script on your Windows development machine

# Define variables
$ImageName = "pickme/Lucid"
$ImageTag = "1.0"
$WorkspaceFolder = "$env:USERPROFILE\Lucid"
$DevContainerFolder = "$WorkspaceFolder\.devcontainer"
$DevContainerJsonPath = "$DevContainerFolder\devcontainer.json"

Write-Host "===== Setting up Lucid DevContainer Environment ====="
Write-Host "Image: $ImageName`:$ImageTag"
Write-Host "Workspace: $WorkspaceFolder"

# Create workspace directory if it doesn't exist
if (-not (Test-Path $WorkspaceFolder)) {
    Write-Host "Creating workspace folder: $WorkspaceFolder"
    New-Item -Path $WorkspaceFolder -ItemType Directory -Force | Out-Null
}

# Create .devcontainer directory if it doesn't exist
if (-not (Test-Path $DevContainerFolder)) {
    Write-Host "Creating .devcontainer folder"
    New-Item -Path $DevContainerFolder -ItemType Directory -Force | Out-Null
}

# Pull the Docker image
Write-Host "Pulling Docker image: $ImageName`:$ImageTag"
docker pull "$ImageName`:$ImageTag"

# Create devcontainer.json file
Write-Host "Creating devcontainer.json configuration"
$devContainerJson = @"
{
  "name": "Lucid Dev",
  "image": "$ImageName`:$ImageTag",
  "workspaceFolder": "/workspaces/Lucid",
  "remoteUser": "root",
  "overrideCommand": true,
  "runArgs": [
    "--platform=linux/arm64",
    "--network=lucid-dev_lucid_net"
  ],
  "containerEnv": {
    "PYTHONUNBUFFERED": "1",
    "DOCKER_DEFAULT_PLATFORM": "linux/arm64"
  },
  "mounts": [
    "source=${WorkspaceFolder},target=/workspaces/Lucid,type=bind"
  ],
  "initializeCommand": "docker network inspect lucid-dev_lucid_net >nul 2>&1 || docker network create --driver bridge --attachable lucid-dev_lucid_net",
  "forwardPorts": [
    8080,
    8081,
    27017,
    9050,
    9051
  ],
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "astral-sh.ruff",
        "ms-python.black-formatter",
        "ms-vscode-remote.remote-containers",
        "ms-azuretools.vscode-docker"
      ]
    }
  }
}
"@

# Save the devcontainer.json file
$devContainerJson | Out-File -FilePath $DevContainerJsonPath -Encoding utf8

# Clone the Lucid repository if it doesn't exist
if (-not (Test-Path "$WorkspaceFolder\.git")) {
    Write-Host "Cloning Lucid repository..."
    Set-Location $WorkspaceFolder
    git clone https://github.com/HamiGames/Lucid.git .
}

Write-Host "===== Setup Complete ====="
Write-Host "Launching VS Code..."

# Launch VS Code with the workspace
code $WorkspaceFolder

Write-Host "VS Code launched. Use the 'Remote-Containers: Reopen in Container' command in VS Code to start the container."
Write-Host "To do this, press F1, type 'Remote-Containers: Reopen in Container', and press Enter."