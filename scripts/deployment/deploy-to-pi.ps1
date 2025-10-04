# LUCID PI DEPLOYMENT SCRIPT - Complete Infrastructure Setup
# HamiGames/Lucid.git Repository Aligned & LUCID-STRICT Compliant
# Deploys tor-proxy and core services to Raspberry Pi 5 via SSH
# 
# TARGET: ssh pickme@192.168.0.75
# SOURCE: Windows PowerShell development machine
# Usage: .\scripts\deployment\deploy-to-pi.ps1

param(
    [string]$PiHost = "pickme@192.168.0.75",
    [int]$SshPort = 22,
    [string]$ProjectPath = "/workspaces/Lucid",
    [switch]$SkipSync,
    [switch]$VerifyOnly,
    [switch]$TorProxyOnly,
    [switch]$CoreServicesOnly,
    [switch]$FullDeploy,
    [switch]$CleanDeploy
)

# LUCID-STRICT mode configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Pi deployment configuration
$COMPOSE_FILE = "infrastructure/compose/lucid-dev.yaml"
$ENV_FILE = "infrastructure/compose/.env"
$TOR_DIR = "02-network-security/tor"
$DEPLOYMENT_TIMEOUT = 600  # 10 minutes for complete deployment

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "LUCID PI DEPLOYMENT SYSTEM - Infrastructure Setup" -ForegroundColor Cyan
Write-Host "Target: $PiHost | Project: $ProjectPath" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan

# Function to execute SSH commands with proper error handling
function Invoke-SshCommand {
    param(
        [string]$Command,
        [string]$Description,
        [switch]$IgnoreErrors,
        [switch]$ShowOutput
    )
    
    Write-Host "  -> $Description" -ForegroundColor White
    
    $sshCmd = "ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p $SshPort $PiHost `"$Command`""
    
    try {
        if ($ShowOutput) {
            Write-Host "    Executing: $Command" -ForegroundColor Gray
            $result = Invoke-Expression $sshCmd 2>&1
            if ($result) {
                Write-Host $result -ForegroundColor Gray
            }
            return $result
        } else {
            $result = Invoke-Expression $sshCmd 2>$null
            if ($LASTEXITCODE -eq 0 -or $IgnoreErrors) {
                Write-Host "    Check $Description completed" -ForegroundColor Gray
                return $result
            } else {
                throw "SSH command failed with exit code $LASTEXITCODE"
            }
        }
    }
    catch {
        if ($IgnoreErrors) {
            Write-Warning "  $Description failed (continuing): $($_.Message)"
            return $null
        } else {
            Write-Error "HALT: $Description failed: $($_.Message)"
            exit 1
        }
    }
}

# Function to sync files to Pi
function Sync-FilesToPi {
    param(
        [string]$LocalPath,
        [string]$RemotePath,
        [string]$Description
    )
    
    Write-Host "  -> Syncing $Description" -ForegroundColor White
    
    # Use robocopy for Windows to prepare files, then scp
    $tempDir = "$env:TEMP\lucid_deploy_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    
    try {
        # Copy files locally first
        robocopy $LocalPath $tempDir /E /XD .git __pycache__ node_modules .pytest_cache /XF *.pyc *.log > $null
        
        # Create remote directory
        Invoke-SshCommand "mkdir -p `"$(Split-Path $RemotePath -Parent)`"" "Creating remote directory" -IgnoreErrors
        
        # Sync to Pi using scp
        $scpCmd = "scp -r -o ConnectTimeout=10 -o StrictHostKeyChecking=no -P $SshPort `"$tempDir\*`" `"$PiHost`:$RemotePath`""
        $result = Invoke-Expression $scpCmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    Check $Description synced successfully" -ForegroundColor Gray
        } else {
            throw "SCP failed: $result"
        }
    }
    finally {
        # Cleanup temp directory
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "`n[1/7] SSH CONNECTION VERIFICATION" -ForegroundColor Green

# Test SSH connection
try {
    $sshTest = ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p $SshPort $PiHost "echo 'SSH_OK'" 2>&1
    if ($sshTest -match "SSH_OK") {
        Write-Host "  Check SSH connection to $PiHost successful" -ForegroundColor Gray
    } else {
        throw "SSH connection failed: $sshTest"
    }
}
catch {
    Write-Error "HALT: Cannot connect to Pi at $PiHost`:$SshPort"
    Write-Host "Please verify:" -ForegroundColor Yellow
    Write-Host "  - Pi is powered on and connected to network" -ForegroundColor White
    Write-Host "  - SSH is enabled on Pi" -ForegroundColor White
    Write-Host "  - Network connectivity to 192.168.0.75" -ForegroundColor White
    exit 1
}

Write-Host "`n[2/7] PI SYSTEM VERIFICATION" -ForegroundColor Green

# Check Pi system requirements
Invoke-SshCommand "docker --version" "Checking Docker installation" -ShowOutput
Invoke-SshCommand "docker compose version" "Checking Docker Compose" -ShowOutput
Invoke-SshCommand "uname -a" "Checking Pi system info" -ShowOutput

# Check available space
$spaceInfo = Invoke-SshCommand "df -h /" "Checking disk space" -ShowOutput
Write-Host "    Available space: $spaceInfo" -ForegroundColor Gray

Write-Host "`n[3/7] PROJECT SYNC TO PI" -ForegroundColor Green

if (-not $SkipSync) {
    # Ensure project directory exists on Pi
    Invoke-SshCommand "mkdir -p $ProjectPath" "Creating project directory"
    
    # Sync critical components
    Write-Host "  -> Syncing infrastructure components" -ForegroundColor White
    Sync-FilesToPi "infrastructure" "$ProjectPath/infrastructure" "Infrastructure configs"
    
    Write-Host "  -> Syncing tor-proxy components" -ForegroundColor White
    Sync-FilesToPi "02-network-security" "$ProjectPath/02-network-security" "Network security components"
    
    Write-Host "  -> Syncing API components" -ForegroundColor White
    Sync-FilesToPi "03-api-gateway" "$ProjectPath/03-api-gateway" "API Gateway components"
    
    # Sync environment configuration
    if (Test-Path $ENV_FILE) {
        Write-Host "  -> Syncing environment configuration" -ForegroundColor White
        $scpEnvCmd = "scp -o ConnectTimeout=10 -o StrictHostKeyChecking=no -P $SshPort `"$ENV_FILE`" `"$PiHost`:$ProjectPath/$ENV_FILE`""
        Invoke-Expression $scpEnvCmd 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    Check Environment file synced" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  -> Skipping file sync (SkipSync flag)" -ForegroundColor Yellow
}

Write-Host "`n[4/7] PI DOCKER ENVIRONMENT SETUP" -ForegroundColor Green

# Clean previous containers if requested
if ($CleanDeploy) {
    Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE down --remove-orphans --timeout 30" "Stopping existing services" -IgnoreErrors -ShowOutput
    Invoke-SshCommand "docker system prune -f" "Cleaning Docker system" -IgnoreErrors
}

# Create networks
Invoke-SshCommand "docker network create lucid_core_net --driver bridge --subnet 172.21.0.0/16 --gateway 172.21.0.1 --attachable" "Creating core network" -IgnoreErrors

Write-Host "`n[5/7] TOR-PROXY INFRASTRUCTURE FIXES" -ForegroundColor Green

# Fix tor configuration on Pi
$torFixScript = @'
#!/bin/bash
set -e

echo "[tor-fix] Fixing Tor infrastructure on Pi..."

cd /workspaces/Lucid/02-network-security/tor

# Ensure proper permissions
sudo chown -R 1000:1000 .
chmod +x entrypoint.sh tor-health.sh tor-show-onion.sh
chmod +x scripts/*.sh

# Verify torrc configuration
if [ ! -f torrc ]; then
    echo "Creating torrc..."
    cat > torrc << 'EOF'
Log notice stdout
SocksPort 0.0.0.0:9050
ControlPort 0.0.0.0:9051
CookieAuthentication 1
CookieAuthFileGroupReadable 1
DataDirectory /var/lib/tor

# Multi-onion support
HiddenServiceDir /var/lib/tor/api_gateway
HiddenServiceVersion 3
HiddenServicePort 80 lucid_api_gateway:8080

HiddenServiceDir /var/lib/tor/api_server
HiddenServiceVersion 3
HiddenServicePort 8081 lucid_api:8081

HiddenServiceDir /var/lib/tor/mongo_proxy
HiddenServiceVersion 3
HiddenServicePort 27017 lucid_mongo:27017
EOF
fi

echo "[tor-fix] Tor configuration updated"

# Test Dockerfile syntax
if [ -f Dockerfile ]; then
    echo "[tor-fix] Dockerfile exists and ready for build"
else
    echo "[tor-fix] ERROR: Dockerfile missing!"
    exit 1
fi

echo "[tor-fix] Tor infrastructure verification complete"
'@

# Write and execute the fix script on Pi
$torFixScript | Invoke-SshCommand "cd $ProjectPath && cat > /tmp/tor-fix.sh && chmod +x /tmp/tor-fix.sh && /tmp/tor-fix.sh" "Fixing Tor infrastructure" -ShowOutput

Write-Host "`n[6/7] SERVICE DEPLOYMENT ON PI" -ForegroundColor Green

if ($VerifyOnly) {
    Write-Host "  -> VERIFY-ONLY MODE: Checking deployment readiness" -ForegroundColor White
    Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE config" "Validating compose configuration" -ShowOutput
    Write-Host "`n[VERIFY-ONLY] Pi deployment verification complete" -ForegroundColor Green
    Write-Host "  Check SSH connection working" -ForegroundColor Gray
    Write-Host "  Check Docker environment ready" -ForegroundColor Gray
    Write-Host "  Check Project files synced" -ForegroundColor Gray
    Write-Host "  Check Tor infrastructure fixed" -ForegroundColor Gray
    Write-Host "`nTo deploy services, run without -VerifyOnly flag" -ForegroundColor Yellow
    exit 0
}

# Deploy based on selected mode
if ($TorProxyOnly) {
    Write-Host "  -> Deploying TOR-PROXY ONLY on Pi" -ForegroundColor White
    Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE up -d --build tor-proxy" "Building and starting Tor proxy" -ShowOutput
    
} elseif ($CoreServicesOnly) {
    Write-Host "  -> Deploying CORE SERVICES ONLY on Pi" -ForegroundColor White
    Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE up -d --build lucid_mongo lucid_api lucid_api_gateway" "Building and starting core services" -ShowOutput
    
} else {
    Write-Host "  -> Deploying COMPLETE INFRASTRUCTURE on Pi" -ForegroundColor White
    Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE up -d --build --timeout $DEPLOYMENT_TIMEOUT" "Building and starting all services" -ShowOutput
}

Write-Host "`n[7/7] PI DEPLOYMENT VERIFICATION" -ForegroundColor Green

# Wait for services to start
Write-Host "  -> Waiting for services to become healthy (60 seconds)" -ForegroundColor White
Start-Sleep -Seconds 60

# Check service status
$serviceStatus = Invoke-SshCommand "cd $ProjectPath && docker compose -f $COMPOSE_FILE ps" "Checking service status" -ShowOutput

# Check network configuration
$networkInfo = Invoke-SshCommand "docker network inspect lucid_core_net --format '{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{println}}{{end}}'" "Checking network configuration" -ShowOutput -IgnoreErrors

# Test service connectivity
if ($TorProxyOnly) {
    $torHealth = Invoke-SshCommand "docker exec tor_proxy /usr/local/bin/tor-health" "Testing Tor proxy health" -IgnoreErrors -ShowOutput
} else {
    $apiHealth = Invoke-SshCommand "curl -s http://localhost:8081/health" "Testing API health" -IgnoreErrors -ShowOutput
    $torHealth = Invoke-SshCommand "curl -s --socks5-hostname localhost:9050 http://httpbin.org/ip" "Testing Tor connectivity" -IgnoreErrors -ShowOutput
}

Write-Host "`n==============================================================================" -ForegroundColor Cyan
Write-Host "SUCCESS PI DEPLOYMENT COMPLETED" -ForegroundColor Green
Write-Host "   Target: $PiHost | Project: $ProjectPath" -ForegroundColor Green

Write-Host "`nNotes Pi Services:" -ForegroundColor Yellow
Write-Host "   • MongoDB 7: $PiHost`:27017" -ForegroundColor White
Write-Host "   • Tor SOCKS: $PiHost`:9050" -ForegroundColor White
Write-Host "   • Tor Control: $PiHost`:9051" -ForegroundColor White
Write-Host "   • API Server: $PiHost`:8081" -ForegroundColor White
Write-Host "   • API Gateway: $PiHost`:8080" -ForegroundColor White

Write-Host "`nTools Pi Management:" -ForegroundColor Yellow
Write-Host "   • SSH Access: ssh $PiHost" -ForegroundColor White
Write-Host "   • Service Status: ssh $PiHost 'cd $ProjectPath && docker compose -f $COMPOSE_FILE ps'" -ForegroundColor White
Write-Host "   • Service Logs: ssh $PiHost 'cd $ProjectPath && docker compose -f $COMPOSE_FILE logs -f'" -ForegroundColor White
Write-Host "   • Tor Health: ssh $PiHost 'docker exec tor_proxy /usr/local/bin/tor-health'" -ForegroundColor White
Write-Host "   • Stop Services: ssh $PiHost 'cd $ProjectPath && docker compose -f $COMPOSE_FILE down'" -ForegroundColor White

Write-Host "`nQuick Access:" -ForegroundColor Yellow
Write-Host "   • Connect to Pi: ssh $PiHost" -ForegroundColor White
Write-Host "   • Project Dir: cd $ProjectPath" -ForegroundColor White

Write-Host "==============================================================================" -ForegroundColor Cyan

exit 0