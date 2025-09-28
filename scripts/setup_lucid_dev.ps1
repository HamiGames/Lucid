# Path: scripts/setup_lucid_dev.ps1
# Development environment setup script

param(
    [string]$PythonVersion = "3.12",
    [switch]$InstallDeps = $true
)

Write-Host "Setting up Lucid RDP development environment..." -ForegroundColor Green

if ($InstallDeps) {
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    pip install -r .devcontainer/requirements-dev.txt
}

Write-Host "Lucid RDP development environment ready!" -ForegroundColor Green
