# LUCID PI DEPLOYMENT - Simple Password Authentication
# No SSH key passphrases - uses password authentication
# Usage: .\scripts\deployment\deploy-pi-simple.ps1

param(
    [string]$PiHost = "192.168.0.75",
    [string]$PiUser = "pickme", 
    [string]$ProjectPath = "/home/pickme/lucid",
    [switch]$TorProxyOnly,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Continue"

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "LUCID PI DEPLOYMENT - Simple Authentication" -ForegroundColor Cyan
Write-Host "Target: $PiUser@$PiHost | Project: $ProjectPath" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan

Write-Host "`nNote: This will prompt for the Pi user password (pickme@192.168.0.75)" -ForegroundColor Yellow
Write-Host "If you want passwordless SSH, set up SSH key authentication first.`n" -ForegroundColor Gray

# Simple SSH command function
function Invoke-PiCommand {
    param(
        [string]$Command,
        [string]$Description
    )
    
    Write-Host "  -> $Description" -ForegroundColor White
    Write-Host "    Command: $Command" -ForegroundColor Gray
    
    # Use sshpass if available, otherwise regular ssh (will prompt for password)
    ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password $PiUser@$PiHost $Command
}

Write-Host "[1/4] SSH CONNECTION TEST" -ForegroundColor Green
try {
    $testResult = ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o PreferredAuthentications=password $PiUser@$PiHost "echo 'CONNECTION_OK'"
    if ($testResult -match "CONNECTION_OK") {
        Write-Host "  Check SSH connection successful" -ForegroundColor Gray
    }
}
catch {
    Write-Error "Cannot connect to Pi. Please verify the Pi is accessible and you know the password."
    exit 1
}

Write-Host "`n[2/4] DIRECTORY SETUP" -ForegroundColor Green
Invoke-PiCommand "mkdir -p $ProjectPath" "Creating project directory"
Invoke-PiCommand "sudo chown -R $PiUser`:$PiUser $ProjectPath" "Setting directory permissions"

Write-Host "`n[3/4] FILE SYNC" -ForegroundColor Green
Write-Host "  -> Syncing critical files to Pi" -ForegroundColor White

# Sync infrastructure files
Write-Host "    Syncing infrastructure..." -ForegroundColor Gray
scp -r -o StrictHostKeyChecking=no -o PreferredAuthentications=password infrastructure $PiUser@$PiHost`:$ProjectPath/

# Sync tor components  
Write-Host "    Syncing tor-proxy..." -ForegroundColor Gray
scp -r -o StrictHostKeyChecking=no -o PreferredAuthentications=password 02-network-security $PiUser@$PiHost`:$ProjectPath/

# Sync API components
Write-Host "    Syncing API components..." -ForegroundColor Gray
scp -r -o StrictHostKeyChecking=no -o PreferredAuthentications=password 03-api-gateway $PiUser@$PiHost`:$ProjectPath/

if ($VerifyOnly) {
    Write-Host "`n[VERIFY-ONLY] Pi setup complete" -ForegroundColor Green
    Invoke-PiCommand "ls -la $ProjectPath" "Checking synced files"
    exit 0
}

Write-Host "`n[4/4] DOCKER DEPLOYMENT" -ForegroundColor Green

# Create Docker network
Invoke-PiCommand "docker network create lucid_core_net --subnet 172.21.0.0/16 --gateway 172.21.0.1 --attachable || echo 'Network exists'" "Creating Docker network"

# Deploy services
if ($TorProxyOnly) {
    Write-Host "  -> Building TOR-PROXY on Pi (ARM64)" -ForegroundColor White
    Invoke-PiCommand "cd $ProjectPath && docker compose -f infrastructure/compose/lucid-dev.yaml up -d --build tor-proxy" "Building Tor proxy"
} else {
    Write-Host "  -> Building ALL SERVICES on Pi (ARM64)" -ForegroundColor White  
    Invoke-PiCommand "cd $ProjectPath && docker compose -f infrastructure/compose/lucid-dev.yaml up -d --build" "Building all services"
}

# Check status
Write-Host "`n  -> Checking deployment status" -ForegroundColor White
Invoke-PiCommand "cd $ProjectPath && docker compose -f infrastructure/compose/lucid-dev.yaml ps" "Service status"

Write-Host "`n==============================================================================" -ForegroundColor Cyan
Write-Host "SUCCESS Pi deployment completed!" -ForegroundColor Green
Write-Host "Services running on: $PiUser@$PiHost" -ForegroundColor Green
Write-Host "`nTo check status: ssh $PiUser@$PiHost 'cd $ProjectPath && docker compose -f infrastructure/compose/lucid-dev.yaml ps'" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan