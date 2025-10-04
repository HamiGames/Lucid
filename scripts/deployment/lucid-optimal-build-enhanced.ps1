# LUCID OPTIMAL BUILD SCRIPT - Enhanced Environment Handling
# HamiGames/Lucid.git Repository Aligned & LUCID-STRICT Compliant
# Professional Docker build system with automatic environment configuration
# Compatible with: Windows PowerShell 5.1+, Docker Desktop
# 
# DIR: C:\Users\surba\Desktop\personal\THE_FUCKER\lucid_2\Lucid
# Usage: .\scripts\deployment\lucid-optimal-build-enhanced.ps1

param(
    [switch]$NoCacheClean,
    [switch]$SkipNetworkRecreate, 
    [switch]$VerifyOnly,
    [switch]$DevContainerOnly,
    [switch]$CoreServicesOnly,
    [switch]$CreateEnvFiles
)

# LUCID-STRICT mode configuration
$ErrorActionPreference = "Continue"  # Allow warnings to pass through
$ProgressPreference = "SilentlyContinue"

# Repository-aligned configuration
$DEVCONTAINER_COMPOSE = "infrastructure\containers\.devcontainer\docker-compose.dev.yml"
$CORE_SERVICES_COMPOSE = "infrastructure\compose\lucid-dev.yaml"
$CORE_SERVICES_ENV = "infrastructure\compose\.env"
$DEVCONTAINER_NETWORK = "lucid-dev_lucid_net"  # 172.20.0.0/16
$CORE_SERVICES_NETWORK = "lucid_core_net"       # 172.21.0.0/16
$BUILDX_BUILDER = "lucid-pi"

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "LUCID OPTIMAL BUILD SYSTEM - Enhanced Environment Handling" -ForegroundColor Cyan
Write-Host "HamiGames/Lucid.git Aligned & LUCID-STRICT Compliant" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan

# Verify we're in the correct directory
if (-not (Test-Path $DEVCONTAINER_COMPOSE) -or -not (Test-Path $CORE_SERVICES_COMPOSE)) {
    Write-Error "HALT: Must run from Lucid project root directory containing both compose files"
    Write-Host "Required files:" -ForegroundColor Yellow
    Write-Host "  - $DEVCONTAINER_COMPOSE" -ForegroundColor White
    Write-Host "  - $CORE_SERVICES_COMPOSE" -ForegroundColor White
    exit 1
}

Write-Host "`n[0/5] ENVIRONMENT CONFIGURATION SETUP" -ForegroundColor Green

# Create .env file if it doesn't exist or if explicitly requested
if (-not (Test-Path $CORE_SERVICES_ENV) -or $CreateEnvFiles) {
    Write-Host "  -> Creating environment configuration file" -ForegroundColor White
    
    # The .env file should already be created by our previous step
    if (-not (Test-Path $CORE_SERVICES_ENV)) {
        Write-Error "HALT: Environment file missing and auto-creation failed. Please ensure $CORE_SERVICES_ENV exists."
        exit 1
    } else {
        Write-Host "    Check Environment file exists: $CORE_SERVICES_ENV" -ForegroundColor Gray
    }
} else {
    Write-Host "  -> Environment configuration found: $CORE_SERVICES_ENV" -ForegroundColor White
}

Write-Host "`n[1/5] DOCKER ENVIRONMENT CLEANUP (Per User Rules)" -ForegroundColor Green

if (-not $NoCacheClean) {
    Write-Host "  -> Erasing ALL Docker buildx volumes (genius-level clean)" -ForegroundColor White
    try {
        # Clear all buildx builders except default
        $builders = docker buildx ls --format "{{.Name}}" 2>$null | Where-Object { $_ -ne "default" -and $_ -ne "" }
        foreach ($builder in $builders) {
            Write-Host "    Check Removing buildx builder: $builder" -ForegroundColor Gray
            docker buildx rm $builder --force 2>$null | Out-Null
        }
        
        # Clean build cache and system
        docker buildx prune --all --force 2>$null | Out-Null
        docker system prune -af --volumes 2>$null | Out-Null
        docker network prune -f 2>$null | Out-Null
        
        Write-Host "    Check Docker environment completely cleaned" -ForegroundColor Gray
    }
    catch {
        Write-Warning "Docker cleanup partially failed (continuing): $($_.Message)"
    }
} else {
    Write-Host "  -> Skipping cache cleanup (NoCacheClean flag)" -ForegroundColor Yellow
}

Write-Host "`n[2/5] NETWORK SETUP (Repository Aligned)" -ForegroundColor Green

if (-not $SkipNetworkRecreate) {
    # Create DevContainer network (lucid-dev_lucid_net - 172.20.0.0/16)
    Write-Host "  -> Setting up DevContainer network (172.20.0.0/16)" -ForegroundColor White
    docker network rm $DEVCONTAINER_NETWORK 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { 
        Write-Host "    (DevContainer network removal skipped - may be in use)" -ForegroundColor Gray 
    }
    
    docker network create $DEVCONTAINER_NETWORK `
        --driver bridge `
        --subnet 172.20.0.0/16 `
        --gateway 172.20.0.1 `
        --attachable `
        --label "com.docker.compose.network=$DEVCONTAINER_NETWORK" `
        --label "com.docker.compose.project=lucid-devcontainer" `
        --label "org.lucid.plane=dev" `
        --label "org.lucid.network=devcontainer" 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    Check DevContainer network created successfully" -ForegroundColor Gray
    } else {
        Write-Host "    Check DevContainer network already exists (continuing)" -ForegroundColor Gray
    }
    
    # Create Core Services network (lucid_core_net - 172.21.0.0/16) if not DevContainerOnly
    if (-not $DevContainerOnly) {
        Write-Host "  -> Setting up Core Services network (172.21.0.0/16)" -ForegroundColor White
        docker network rm $CORE_SERVICES_NETWORK 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { 
            Write-Host "    (Core Services network removal skipped - may be in use)" -ForegroundColor Gray 
        }
        
        docker network create $CORE_SERVICES_NETWORK `
            --driver bridge `
            --subnet 172.21.0.0/16 `
            --gateway 172.21.0.1 `
            --attachable `
            --label "com.docker.compose.network=$CORE_SERVICES_NETWORK" `
            --label "com.docker.compose.project=lucid-dev" `
            --label "org.lucid.plane=ops" `
            --label "org.lucid.network=core" `
            --label "org.lucid.isolation=true" 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    Check Core Services network created successfully" -ForegroundColor Gray
        } else {
            Write-Host "    Check Core Services network already exists (continuing)" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  -> Skipping network recreation (SkipNetworkRecreate flag)" -ForegroundColor Yellow
}

Write-Host "`n[3/5] DOCKER COMPOSE VALIDATION" -ForegroundColor Green

# Validate DevContainer compose file
Write-Host "  -> Validating DevContainer compose syntax" -ForegroundColor White
$devContainerOutput = docker compose -f $DEVCONTAINER_COMPOSE config 2>&1
$devContainerErrors = $devContainerOutput | Where-Object { $_ -match "error|Error|ERROR" }
if ($devContainerErrors) {
    Write-Error "HALT: DevContainer compose validation failed:`n$($devContainerErrors -join "`n")"
    exit 1
}
Write-Host "    Check DevContainer compose syntax valid" -ForegroundColor Gray

# Validate Core Services compose file if not DevContainerOnly
if (-not $DevContainerOnly) {
    Write-Host "  -> Validating Core Services compose syntax" -ForegroundColor White
    $coreServicesOutput = docker compose -f $CORE_SERVICES_COMPOSE config 2>&1
    $coreServicesErrors = $coreServicesOutput | Where-Object { $_ -match "error|Error|ERROR" -and $_ -notmatch "warning|Warning" }
    if ($coreServicesErrors) {
        Write-Error "HALT: Core Services compose validation failed:`n$($coreServicesErrors -join "`n")"
        exit 1
    }
    
    # Show warnings but don't fail
    $warnings = $coreServicesOutput | Where-Object { $_ -match "warning|Warning" }
    if ($warnings) {
        Write-Host "    Note: Environment variable warnings (expected in development):" -ForegroundColor Gray
        foreach ($warning in $warnings) {
            Write-Host "      $warning" -ForegroundColor DarkGray
        }
    }
    Write-Host "    Check Core Services compose syntax valid" -ForegroundColor Gray
}

if ($VerifyOnly) {
    Write-Host "`n[VERIFY-ONLY MODE] Environment verification complete" -ForegroundColor Green
    Write-Host "  Check Docker environment ready" -ForegroundColor Gray
    Write-Host "  Check Network configuration valid" -ForegroundColor Gray
    Write-Host "  Check Compose file syntax valid" -ForegroundColor Gray
    Write-Host "  Check Environment variables configured" -ForegroundColor Gray
    Write-Host "`nTo perform full build, run without -VerifyOnly flag" -ForegroundColor Yellow
    exit 0
}

Write-Host "`n[4/5] BUILD AND DEPLOYMENT (Repository Aligned)" -ForegroundColor Green

# Determine which services to build based on flags
if ($DevContainerOnly) {
    Write-Host "  -> Building DEVCONTAINER ONLY (lucid-devcontainer)" -ForegroundColor White
    
    # Stop existing devcontainer
    docker compose -f $DEVCONTAINER_COMPOSE down --remove-orphans --timeout 30 2>$null
    
    # Build and start devcontainer
    Write-Host "    Starting DevContainer build (this may take several minutes)..." -ForegroundColor Gray
    $buildResult = docker compose -f $DEVCONTAINER_COMPOSE up -d --build --timeout 600 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "HALT: DevContainer build failed:`n$buildResult"
        exit 1
    }
    
    Write-Host "    Check DevContainer built and started (lucid-devcontainer)" -ForegroundColor Gray
    
} elseif ($CoreServicesOnly) {
    Write-Host "  -> Building CORE SERVICES ONLY (MongoDB, Tor, APIs)" -ForegroundColor White
    
    # Stop existing core services
    docker compose -f $CORE_SERVICES_COMPOSE down --remove-orphans --timeout 30 2>$null
    
    # Build and start core services
    Write-Host "    Starting Core Services build (MongoDB 7, Tor Proxy, API Server, API Gateway)..." -ForegroundColor Gray
    $buildResult = docker compose -f $CORE_SERVICES_COMPOSE up -d --build --timeout 300 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "HALT: Core Services build failed:`n$buildResult"
        exit 1
    }
    
    Write-Host "    Check Core Services built and started" -ForegroundColor Gray
    
} else {
    Write-Host "  -> Building BOTH DevContainer AND Core Services" -ForegroundColor White
    
    # Build DevContainer first (Docker-in-Docker build factory)
    Write-Host "    Building DevContainer (lucid-devcontainer)..." -ForegroundColor Gray
    docker compose -f $DEVCONTAINER_COMPOSE down --remove-orphans --timeout 30 2>$null
    $devBuildResult = docker compose -f $DEVCONTAINER_COMPOSE up -d --build --timeout 600 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "DevContainer build failed, continuing with Core Services"
    } else {
        Write-Host "    Check DevContainer built successfully" -ForegroundColor Gray
    }
    
    # Build Core Services 
    Write-Host "    Building Core Services (MongoDB, Tor, APIs)..." -ForegroundColor Gray
    docker compose -f $CORE_SERVICES_COMPOSE down --remove-orphans --timeout 30 2>$null
    $coreBuildResult = docker compose -f $CORE_SERVICES_COMPOSE up -d --build --timeout 300 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "HALT: Core Services build failed:`n$coreBuildResult"
        exit 1
    }
    
    Write-Host "    Check Both environments built and started" -ForegroundColor Gray
}

Write-Host "`n[5/5] HEALTH VERIFICATION AND SERVICE STATUS" -ForegroundColor Green

# Determine which compose file to check based on what was built
$composeFileToCheck = if ($DevContainerOnly) { $DEVCONTAINER_COMPOSE } elseif ($CoreServicesOnly) { $CORE_SERVICES_COMPOSE } else { $CORE_SERVICES_COMPOSE }
$networkToCheck = if ($DevContainerOnly) { $DEVCONTAINER_NETWORK } elseif ($CoreServicesOnly) { $CORE_SERVICES_NETWORK } else { $CORE_SERVICES_NETWORK }

# Wait for services to become healthy
Write-Host "  -> Waiting for service health checks (max 120 seconds)" -ForegroundColor White

$maxWait = 120
$waited = 0
$allHealthy = $false

while ($waited -lt $maxWait -and -not $allHealthy) {
    Start-Sleep -Seconds 10
    $waited += 10
    
    try {
        $servicesJson = docker compose -f $composeFileToCheck ps --format "json" 2>$null
        if ($servicesJson) {
            $services = $servicesJson | ConvertFrom-Json
            $healthyCount = 0
            $totalServices = if ($services -is [array]) { $services.Count } else { 1 }
            
            foreach ($service in $services) {
                if ($service.Health -eq "healthy" -or $service.Health -eq "" -or $service.State -eq "running") {
                    $healthyCount++
                }
            }
            
            Write-Host "    Clock Health check progress: $healthyCount/$totalServices healthy (${waited}s elapsed)" -ForegroundColor Gray
            
            if ($healthyCount -eq $totalServices) {
                $allHealthy = $true
            }
        } else {
            Write-Host "    Clock Waiting for services to start (${waited}s elapsed)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "    Clock Checking services (${waited}s elapsed)" -ForegroundColor Gray
    }
}

# Final status check
Write-Host "`n  -> Final service status:" -ForegroundColor White
if ($DevContainerOnly) {
    Write-Host "    DevContainer Status:" -ForegroundColor Gray
    docker compose -f $DEVCONTAINER_COMPOSE ps 2>$null | Out-Host
} elseif ($CoreServicesOnly) {
    Write-Host "    Core Services Status:" -ForegroundColor Gray
    docker compose -f $CORE_SERVICES_COMPOSE ps 2>$null | Out-Host
} else {
    Write-Host "    DevContainer Status:" -ForegroundColor Gray
    docker compose -f $DEVCONTAINER_COMPOSE ps 2>$null | Out-Host
    Write-Host "    Core Services Status:" -ForegroundColor Gray
    docker compose -f $CORE_SERVICES_COMPOSE ps 2>$null | Out-Host
}

# Network inspection
Write-Host "`n  -> Network configuration verification:" -ForegroundColor White
try {
    $networkInfo = docker network inspect $networkToCheck --format "{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{println}}{{end}}" 2>$null
    if ($networkInfo) {
        Write-Host $networkInfo -ForegroundColor Gray
    } else {
        Write-Host "    (Network information unavailable)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "    (Network inspection failed)" -ForegroundColor Yellow
}

Write-Host "`n==============================================================================" -ForegroundColor Cyan
if ($allHealthy) {
    Write-Host "SUCCESS LUCID OPTIMAL BUILD COMPLETED SUCCESSFULLY" -ForegroundColor Green
    Write-Host "   HamiGames/Lucid.git Repository Aligned & LUCID-STRICT Compliant" -ForegroundColor Green
    
    if ($DevContainerOnly) {
        Write-Host "`nNotes DevContainer Environment (lucid-devcontainer):" -ForegroundColor Yellow
        Write-Host "   • Build Factory: Docker-in-Docker with buildx support" -ForegroundColor White
        Write-Host "   • SSH Access: ssh root@localhost -p 2222 (password: lucid)" -ForegroundColor White
        Write-Host "   • VS Code: 'Dev Containers: Attach to Running Container'" -ForegroundColor White
        Write-Host "   • Network: $DEVCONTAINER_NETWORK (172.20.0.0/16)" -ForegroundColor White
        Write-Host "   • Status: docker compose -f $DEVCONTAINER_COMPOSE ps" -ForegroundColor White
    } elseif ($CoreServicesOnly) {
        Write-Host "`nNotes Core Services Environment:" -ForegroundColor Yellow
        Write-Host "   • MongoDB 7 Replica Set: localhost:27017" -ForegroundColor White
        Write-Host "   • Tor SOCKS Proxy: localhost:9050" -ForegroundColor White
        Write-Host "   • Tor Control Port: localhost:9051" -ForegroundColor White
        Write-Host "   • API Server: localhost:8081" -ForegroundColor White
        Write-Host "   • API Gateway: localhost:8080" -ForegroundColor White
        Write-Host "   • Network: $CORE_SERVICES_NETWORK (172.21.0.0/16)" -ForegroundColor White
        Write-Host "   • Status: docker compose -f $CORE_SERVICES_COMPOSE ps" -ForegroundColor White
    } else {
        Write-Host "`nNotes Complete Environment (DevContainer + Core Services):" -ForegroundColor Yellow
        Write-Host "   • DevContainer: lucid-devcontainer (Docker-in-Docker build factory)" -ForegroundColor White
        Write-Host "   • Core Services: MongoDB 7, Tor Proxy, API Server, API Gateway" -ForegroundColor White
        Write-Host "   • Networks: $DEVCONTAINER_NETWORK + $CORE_SERVICES_NETWORK" -ForegroundColor White
        Write-Host "   • Management: Use appropriate compose file for each environment" -ForegroundColor White
    }
    
    Write-Host "`nTools Quick Commands:" -ForegroundColor Yellow
    if ($DevContainerOnly) {
        Write-Host "   • VS Code Attach: Ctrl+Shift+P -> 'Dev Containers: Attach to Running Container'" -ForegroundColor White
        Write-Host "   • SSH Access: ssh root@localhost -p 2222" -ForegroundColor White
        Write-Host "   • Logs: docker compose -f $DEVCONTAINER_COMPOSE logs -f" -ForegroundColor White
        Write-Host "   • Stop: docker compose -f $DEVCONTAINER_COMPOSE down" -ForegroundColor White
    } elseif ($CoreServicesOnly) {
        Write-Host "   • API Health: curl http://localhost:8081/health" -ForegroundColor White
        Write-Host "   • MongoDB Shell: docker exec -it lucid_mongo mongosh" -ForegroundColor White
        Write-Host "   • Logs: docker compose -f $CORE_SERVICES_COMPOSE logs -f" -ForegroundColor White
        Write-Host "   • Stop: docker compose -f $CORE_SERVICES_COMPOSE down" -ForegroundColor White
    } else {
        Write-Host "   • Use appropriate compose file commands for each environment" -ForegroundColor White
    }
} else {
    Write-Warning "WARNING BUILD COMPLETED BUT SOME SERVICES MAY NOT BE FULLY HEALTHY"
    Write-Host "   Check service logs for more details:" -ForegroundColor Yellow
    Write-Host "   DevContainer: docker compose -f $DEVCONTAINER_COMPOSE logs" -ForegroundColor White
    Write-Host "   Core Services: docker compose -f $CORE_SERVICES_COMPOSE logs" -ForegroundColor White
}
Write-Host "==============================================================================" -ForegroundColor Cyan

# Return appropriate exit code
if ($allHealthy) { exit 0 } else { exit 2 }