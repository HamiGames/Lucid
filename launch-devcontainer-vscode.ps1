#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Launch VS Code with Lucid RDP DevContainer
    
.DESCRIPTION
    This script launches VS Code and opens the Lucid RDP project in the devcontainer.
    Should be run after the devcontainer has been built (either locally or on Pi).
    
.PARAMETER Force
    Force rebuild the devcontainer before launching
    
.EXAMPLE
    .\launch-devcontainer-vscode.ps1
    
.EXAMPLE
    .\launch-devcontainer-vscode.ps1 -Force
#>

param(
    [switch]$Force = $false
)

# Color output functions
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }

Write-Info "Lucid RDP DevContainer VS Code Launcher"
Write-Info "========================================"

# Check if we're in the right directory
if (-not (Test-Path ".devcontainer/devcontainer.json")) {
    Write-Error "Not in Lucid project root directory (no .devcontainer found)"
    Write-Info "Please run this script from the Lucid project root directory"
    exit 1
}

Write-Success "Found devcontainer configuration"

# Check if VS Code is installed
try {
    $vscodeVersion = & code --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "VS Code is installed"
        Write-Info "Version: $($vscodeVersion[0])"
    }
} catch {
    Write-Error "VS Code (code command) not found in PATH"
    Write-Info "Please install VS Code or add it to your PATH"
    exit 1
}

# Check if Remote-Containers extension is needed
Write-Info "Checking for Dev Containers extension..."

# Check Docker status
try {
    $dockerInfo = docker info 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker is running"
    } else {
        Write-Error "Docker is not running or not accessible"
        Write-Info "Please start Docker Desktop and try again"
        exit 1
    }
} catch {
    Write-Error "Docker command not found"
    Write-Info "Please install Docker Desktop"
    exit 1
}

# Check if devcontainer image exists
$imageName = "pickme/lucid"
Write-Info "Checking for devcontainer image: $imageName"

$imageExists = docker images --format "table {{.Repository}}:{{.Tag}}" | Select-String "$imageName"
if ($imageExists) {
    Write-Success "DevContainer image found: $imageName"
} else {
    Write-Warning "DevContainer image not found locally"
    if ($Force) {
        Write-Info "Force flag specified, attempting to build..."
        try {
            & .\build-devcontainer.ps1
            if ($LASTEXITCODE -ne 0) {
                Write-Error "DevContainer build failed"
                Write-Info "Try building on the Pi system if this is an ARM64 target"
                exit 1
            }
        } catch {
            Write-Error "Failed to run build script"
            exit 1
        }
    } else {
        Write-Warning "DevContainer image not available"
        Write-Info "Options:"
        Write-Info "1. Run with -Force flag to attempt local build"
        Write-Info "2. Build on Pi system first, then run this script"
        Write-Info "3. Pull the image if it's available in a registry"
        
        $choice = Read-Host "Do you want to attempt local build? (y/N)"
        if ($choice -eq 'y' -or $choice -eq 'Y') {
            Write-Info "Attempting local build..."
            try {
                & .\build-devcontainer.ps1
                if ($LASTEXITCODE -ne 0) {
                    Write-Error "DevContainer build failed"
                    Write-Info "The build may require the Pi system for ARM64 architecture"
                    exit 1
                }
            } catch {
                Write-Error "Failed to run build script"
                exit 1
            }
        } else {
            Write-Info "Please build the devcontainer first, then run this script again"
            exit 1
        }
    }
}

# Check network exists
Write-Info "Checking Docker network..."
$networkExists = docker network ls --format "table {{.Name}}" | Select-String "lucid-dev_lucid_net"
if (-not $networkExists) {
    Write-Info "Creating Docker network: lucid-dev_lucid_net"
    try {
        docker network create --driver bridge --attachable lucid-dev_lucid_net
        Write-Success "Docker network created"
    } catch {
        Write-Warning "Failed to create network, may already exist or have permission issues"
    }
} else {
    Write-Success "Docker network exists: lucid-dev_lucid_net"
}

# Launch VS Code with devcontainer
Write-Info "Launching VS Code with DevContainer..."
Write-Info "This may take a moment while the container starts up..."

try {
    # Open current directory in VS Code with devcontainer
    & code . --folder-uri "vscode-remote://dev-container+$(([System.Web.HttpUtility]::UrlEncode((Get-Location).Path.Replace('\', '/').Replace(':', '%3A'))))/workspaces/Lucid"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "VS Code launched with DevContainer"
        Write-Info "VS Code should now be opening with the Lucid development environment"
        Write-Info ""
        Write-Info "Next steps in VS Code:"
        Write-Info "1. Wait for the devcontainer to fully initialize"
        Write-Info "2. Check that all services are running (MongoDB, Tor)"
        Write-Info "3. Run tests to verify the environment"
        Write-Info "4. Start developing!"
        Write-Info ""
        Write-Info "Available services:"
        Write-Info "• API Gateway: http://localhost:8080"
        Write-Info "• API Server: http://localhost:8081"
        Write-Info "• MongoDB: localhost:27017"
        Write-Info "• Tor SOCKS: localhost:9050"
        Write-Info "• Tor Control: localhost:9051"
    } else {
        Write-Error "Failed to launch VS Code with DevContainer"
        Write-Info "Trying alternative launch method..."
        
        # Try alternative method
        & code .
        Write-Info "VS Code opened. Please use Ctrl+Shift+P and run 'Dev Containers: Reopen in Container'"
    }
} catch {
    Write-Error "Failed to launch VS Code"
    Write-Info "Please try manually:"
    Write-Info "1. Open VS Code"
    Write-Info "2. Open this folder: $(Get-Location)"
    Write-Info "3. Press Ctrl+Shift+P"
    Write-Info "4. Run command: 'Dev Containers: Reopen in Container'"
}

Write-Info ""
Write-Info "DevContainer launch script completed!"