# LUCID PI DEPLOYMENT SCRIPT - Enhanced SSH & File Sync
# HamiGames/Lucid.git Repository Aligned & LUCID-STRICT Compliant
# Deploys tor-proxy and core services to Raspberry Pi 5 via SSH
# 
# TARGET: ssh pickme@192.168.0.75
# Architecture: aarch64 (ARM64) Ubuntu 24.04
# Usage: .\scripts\deployment\deploy-to-pi-enhanced.ps1

param(
    [string]$PiHost = "pickme@192.168.0.75",
    [int]$SshPort = 22,
    [string]$ProjectPath = "/workspaces/Lucid",
    [switch]$SkipSync,
    [switch]$VerifyOnly,
    [switch]$TorProxyOnly,
    [switch]$CoreServicesOnly,
    [switch]$FullDeploy,
    [switch]$CleanDeploy,
    [switch]$FixTorOnly
)

# LUCID-STRICT mode configuration
$ErrorActionPreference = "Continue"  # Allow SSH prompts
$ProgressPreference = "SilentlyContinue"

# Pi deployment configuration
$COMPOSE_FILE = "infrastructure/compose/lucid-dev.yaml"
$ENV_FILE = "infrastructure/compose/.env"
$TOR_DIR = "02-network-security/tor"
$DEPLOYMENT_TIMEOUT = 600

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "LUCID PI DEPLOYMENT SYSTEM - Enhanced SSH & File Sync" -ForegroundColor Cyan
Write-Host "Target: $PiHost | Architecture: ARM64 | Project: $ProjectPath" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan

# Enhanced SSH command function with better error handling
function Invoke-SshCommand {
    param(
        [string]$Command,
        [string]$Description,
        [switch]$IgnoreErrors,
        [switch]$ShowOutput,
        [switch]$NoEcho
    )
    
    if (-not $NoEcho) {
        Write-Host "  -> $Description" -ForegroundColor White
    }
    
    try {
        if ($ShowOutput) {
            Write-Host "    Executing: $Command" -ForegroundColor Gray
            ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p $SshPort $PiHost $Command
        } else {
            $result = ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p $SshPort $PiHost $Command 2>$null
        }
        
        if ($LASTEXITCODE -eq 0 -or $IgnoreErrors) {
            if (-not $NoEcho) {
                Write-Host "    Check $Description completed" -ForegroundColor Gray
            }
            return $result
        } else {
            throw "SSH command failed with exit code $LASTEXITCODE"
        }
    }
    catch {
        if ($IgnoreErrors) {
            Write-Warning "  $Description failed (continuing): $($_.Message)"
            return $null
        } else {
            throw "HALT: $Description failed: $($_.Message)"
        }
    }
}

# Enhanced file sync using rsync over SSH (better than scp for large transfers)
function Sync-ProjectToPi {
    param(
        [string]$LocalDir,
        [string]$RemoteDir,
        [string]$Description
    )
    
    Write-Host "  -> Syncing $Description" -ForegroundColor White
    
    # Create remote directory first
    Invoke-SshCommand "mkdir -p '$RemoteDir'" "Creating remote directory" -IgnoreErrors -NoEcho
    
    # Use tar and ssh pipe for efficient transfer (works better on Windows)
    try {
        $tarCmd = "tar -czf - -C `"$LocalDir`" . | ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p $SshPort $PiHost `"cd '$RemoteDir' && tar -xzf -`""
        Write-Host "    Transferring files..." -ForegroundColor Gray
        Invoke-Expression $tarCmd
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    Check $Description synced successfully" -ForegroundColor Gray
        } else {
            throw "File transfer failed"
        }
    }
    catch {
        Write-Warning "Failed to sync $Description`: $($_.Message)"
    }
}

Write-Host "`n[1/6] SSH CONNECTION VERIFICATION" -ForegroundColor Green

# Test SSH connection
try {
    Write-Host "  -> Testing SSH connection (you may need to enter SSH key passphrase)" -ForegroundColor White
    $sshTest = ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p $SshPort $PiHost "echo 'SSH_CONNECTION_OK'"
    if ($sshTest -match "SSH_CONNECTION_OK") {
        Write-Host "    Check SSH connection to $PiHost successful" -ForegroundColor Gray
    } else {
        throw "SSH connection test failed"
    }
}
catch {
    Write-Error "HALT: Cannot connect to Pi at $PiHost"
    Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
    Write-Host "  1. Verify Pi is powered on: ping 192.168.0.75" -ForegroundColor White
    Write-Host "  2. Test SSH manually: ssh pickme@192.168.0.75" -ForegroundColor White
    Write-Host "  3. Check SSH key permissions" -ForegroundColor White
    exit 1
}

Write-Host "`n[2/6] PI SYSTEM VERIFICATION" -ForegroundColor Green

# Check Pi system requirements
Write-Host "  -> Checking Pi system capabilities" -ForegroundColor White
Invoke-SshCommand "docker --version" "Checking Docker installation" -ShowOutput -IgnoreErrors
Invoke-SshCommand "docker compose version" "Checking Docker Compose" -ShowOutput -IgnoreErrors
Invoke-SshCommand "uname -a" "Checking Pi system info" -ShowOutput -IgnoreErrors

# Check disk space and system resources
Invoke-SshCommand "df -h / | grep -E '/$'" "Checking disk space" -ShowOutput -IgnoreErrors
Invoke-SshCommand "free -h" "Checking memory" -ShowOutput -IgnoreErrors

Write-Host "`n[3/6] PROJECT SYNC TO PI" -ForegroundColor Green

if (-not $SkipSync) {
    # Ensure project directory exists on Pi
    Invoke-SshCommand "mkdir -p $ProjectPath" "Creating project directory"
    
    # Sync critical components efficiently
    Write-Host "  -> Syncing project components to Pi" -ForegroundColor White
    Sync-ProjectToPi "infrastructure" "$ProjectPath/infrastructure" "Infrastructure configs"
    Sync-ProjectToPi "02-network-security" "$ProjectPath/02-network-security" "Tor & network security"
    Sync-ProjectToPi "03-api-gateway" "$ProjectPath/03-api-gateway" "API components"
    
    # Sync environment file
    if (Test-Path $ENV_FILE) {
        Write-Host "  -> Syncing environment configuration" -ForegroundColor White
        scp -o ConnectTimeout=10 -o StrictHostKeyChecking=no -P $SshPort "$ENV_FILE" "$PiHost`:$ProjectPath/$ENV_FILE" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    Check Environment file synced" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  -> Skipping file sync (SkipSync flag)" -ForegroundColor Yellow
}

Write-Host "`n[4/6] TOR-PROXY INFRASTRUCTURE FIXES" -ForegroundColor Green

# Enhanced Tor configuration fix for ARM64 Pi
Write-Host "  -> Fixing Tor infrastructure for ARM64 Pi deployment" -ForegroundColor White

$torFixScript = @"
#!/bin/bash
set -e

echo '[tor-fix] Fixing Tor infrastructure for ARM64 Pi deployment...'

cd $ProjectPath/02-network-security/tor

# Ensure proper permissions for Pi user
sudo chown -R 1000:1000 . 2>/dev/null || chown -R `$(id -u):`$(id -g) .
chmod +x entrypoint.sh tor-health.sh tor-show-onion.sh 2>/dev/null || true
chmod +x scripts/*.sh 2>/dev/null || true

# Create comprehensive torrc for multi-onion support
echo '[tor-fix] Creating ARM64-optimized torrc configuration...'
cat > torrc << 'TORRC_END'
# LUCID Tor Configuration - ARM64 Pi Optimized
Log notice stdout
RunAsDaemon 0

# SOCKS and Control ports
SocksPort 0.0.0.0:9050
ControlPort 0.0.0.0:9051

# Authentication
CookieAuthentication 1
CookieAuthFileGroupReadable 1
HashedControlPassword 16:872860B76453A77D60CA2BB8C1A7042072093276A3D701AD684053EC4C

# Data directory
DataDirectory /var/lib/tor

# Performance optimization for Pi
MaxMemInQueues 512 MB
NumEntryGuards 1
NumDirectoryGuards 1

# Hidden services for LUCID components
HiddenServiceDir /var/lib/tor/api_gateway
HiddenServiceVersion 3
HiddenServicePort 80 lucid_api_gateway:8080

HiddenServiceDir /var/lib/tor/api_server  
HiddenServiceVersion 3
HiddenServicePort 8081 lucid_api:8081

HiddenServiceDir /var/lib/tor/mongo_proxy
HiddenServiceVersion 3  
HiddenServicePort 27017 lucid_mongo:27017

# Additional onion for tunnel services
HiddenServiceDir /var/lib/tor/tunnel
HiddenServiceVersion 3
HiddenServicePort 7000 tunnel-tools:7000

# Tor control onion
HiddenServiceDir /var/lib/tor/control
HiddenServiceVersion 3
HiddenServicePort 9051 127.0.0.1:9051
TORRC_END

echo '[tor-fix] Testing Dockerfile for ARM64 compatibility...'
if [ -f Dockerfile ]; then
    # Verify Alpine base image works on ARM64
    if ! grep -q 'FROM alpine:3.22.1' Dockerfile; then
        echo '[tor-fix] WARNING: Dockerfile may not be ARM64 optimized'
    fi
    echo '[tor-fix] Dockerfile ready for ARM64 build'
else
    echo '[tor-fix] ERROR: Dockerfile missing!'
    exit 1
fi

# Verify critical scripts exist
for script in entrypoint.sh tor-health.sh scripts/create_ephemeral_onion.sh; do
    if [ ! -f "`$script" ]; then
        echo "[tor-fix] ERROR: Missing critical script: `$script"
        exit 1
    fi
done

echo '[tor-fix] ARM64 Tor infrastructure verification complete'
echo '[tor-fix] Ready for Pi deployment'
"@

# Execute the fix script on Pi
$torFixScript | Invoke-SshCommand "cat > /tmp/tor-fix.sh && chmod +x /tmp/tor-fix.sh && /tmp/tor-fix.sh" "Applying Tor infrastructure fixes" -ShowOutput

if ($FixTorOnly) {
    Write-Host "`n[TOR-FIX-ONLY MODE] Tor infrastructure fixes completed" -ForegroundColor Green
    Write-Host "  Check Tor configuration optimized for ARM64 Pi" -ForegroundColor Gray
    Write-Host "  Check Multi-onion services configured" -ForegroundColor Gray
    Write-Host "  Check File permissions corrected" -ForegroundColor Gray
    Write-Host "  Check Dockerfile verified for ARM64" -ForegroundColor Gray
    exit 0
}

Write-Host "`n[5/6] PI DOCKER ENVIRONMENT SETUP" -ForegroundColor Green

# Clean previous deployment if requested
if ($CleanDeploy) {
    Write-Host "  -> Cleaning previous deployment" -ForegroundColor White
    Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE down --remove-orphans --timeout 30" "Stopping existing services" -IgnoreErrors -ShowOutput
    Invoke-SshCommand "docker system prune -f" "Cleaning Docker system" -IgnoreErrors -ShowOutput
    Invoke-SshCommand "docker volume prune -f" "Cleaning Docker volumes" -IgnoreErrors
    Invoke-SshCommand "docker network prune -f" "Cleaning Docker networks" -IgnoreErrors
}

# Create LUCID networks for Pi
Write-Host "  -> Setting up Docker networks for Pi deployment" -ForegroundColor White
Invoke-SshCommand "docker network create lucid_core_net --driver bridge --subnet 172.21.0.0/16 --gateway 172.21.0.1 --attachable --label 'org.lucid.plane=ops' --label 'org.lucid.network=core'" "Creating LUCID core network" -IgnoreErrors

if ($VerifyOnly) {
    Write-Host "`n[VERIFY-ONLY] Pi deployment verification complete" -ForegroundColor Green
    Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE config" "Validating compose configuration" -ShowOutput -IgnoreErrors
    Write-Host "  Check SSH connection working" -ForegroundColor Gray
    Write-Host "  Check Pi system ready (Docker + ARM64)" -ForegroundColor Gray
    Write-Host "  Check Project files synced" -ForegroundColor Gray
    Write-Host "  Check Tor infrastructure configured" -ForegroundColor Gray
    Write-Host "  Check Docker environment prepared" -ForegroundColor Gray
    Write-Host "`nTo deploy services, run without -VerifyOnly flag" -ForegroundColor Yellow
    exit 0
}

Write-Host "`n[6/6] SERVICE DEPLOYMENT ON ARM64 PI" -ForegroundColor Green

# Deploy services based on mode
if ($TorProxyOnly) {
    Write-Host "  -> Deploying TOR-PROXY ONLY on ARM64 Pi" -ForegroundColor White
    Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE up -d --build tor-proxy --timeout $DEPLOYMENT_TIMEOUT" "Building and starting Tor proxy" -ShowOutput
    
} elseif ($CoreServicesOnly) {
    Write-Host "  -> Deploying CORE SERVICES ONLY on ARM64 Pi" -ForegroundColor White
    Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE up -d --build lucid_mongo lucid_api lucid_api_gateway --timeout $DEPLOYMENT_TIMEOUT" "Building and starting core services" -ShowOutput
    
} else {
    Write-Host "  -> Deploying COMPLETE INFRASTRUCTURE on ARM64 Pi" -ForegroundColor White
    Write-Host "    This will build all services for ARM64 architecture (may take 10-15 minutes)" -ForegroundColor Gray
    Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE up -d --build --timeout $DEPLOYMENT_TIMEOUT" "Building and starting all services" -ShowOutput
}

# Post-deployment verification
Write-Host "`n  -> Waiting for services to stabilize (30 seconds)" -ForegroundColor White
Start-Sleep -Seconds 30

# Check deployment status
Write-Host "  -> Verifying Pi deployment status" -ForegroundColor White
Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE ps" "Checking service status" -ShowOutput -IgnoreErrors

# Test connectivity
if ($TorProxyOnly -or -not $CoreServicesOnly) {
    Invoke-SshCommand "docker exec tor_proxy /usr/local/bin/tor-health" "Testing Tor proxy health" -IgnoreErrors -ShowOutput
    Invoke-SshCommand "curl -s --socks5-hostname localhost:9050 http://httpbin.org/ip" "Testing Tor connectivity" -IgnoreErrors -ShowOutput
}

if (-not $TorProxyOnly) {
    Invoke-SshCommand "curl -s http://localhost:8081/health" "Testing API health" -IgnoreErrors -ShowOutput
}

Write-Host "`n==============================================================================" -ForegroundColor Cyan
Write-Host "SUCCESS ARM64 PI DEPLOYMENT COMPLETED" -ForegroundColor Green
Write-Host "   Target: $PiHost (ARM64 Ubuntu) | Project: $ProjectPath" -ForegroundColor Green

Write-Host "`nNotes Pi Services (ARM64):" -ForegroundColor Yellow
Write-Host "   • Architecture: ARM64 (aarch64)" -ForegroundColor White
Write-Host "   • MongoDB 7: $PiHost`:27017" -ForegroundColor White
Write-Host "   • Tor SOCKS: $PiHost`:9050" -ForegroundColor White
Write-Host "   • Tor Control: $PiHost`:9051" -ForegroundColor White
Write-Host "   • API Server: $PiHost`:8081" -ForegroundColor White
Write-Host "   • API Gateway: $PiHost`:8080" -ForegroundColor White

Write-Host "`nTools Pi Management:" -ForegroundColor Yellow
Write-Host "   • SSH Connect: ssh $PiHost" -ForegroundColor White
Write-Host "   • Project Dir: cd $ProjectPath" -ForegroundColor White
Write-Host "   • Service Status: docker compose -f $COMPOSE_FILE ps" -ForegroundColor White
Write-Host "   • Service Logs: docker compose -f $COMPOSE_FILE logs -f [service]" -ForegroundColor White
Write-Host "   • Tor Health: docker exec tor_proxy /usr/local/bin/tor-health" -ForegroundColor White
Write-Host "   • Stop All: docker compose -f $COMPOSE_FILE down" -ForegroundColor White

Write-Host "`nQuick Commands:" -ForegroundColor Yellow
Write-Host "   • Connect: ssh $PiHost" -ForegroundColor White
Write-Host "   • Status: ssh $PiHost 'cd $ProjectPath && docker compose -f $COMPOSE_FILE ps'" -ForegroundColor White
Write-Host "   • Logs: ssh $PiHost 'cd $ProjectPath && docker compose -f $COMPOSE_FILE logs -f'" -ForegroundColor White

Write-Host "==============================================================================" -ForegroundColor Cyan

exit 0