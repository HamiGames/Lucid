# Start LUCID RDP Cluster
# SPEC-4 compliant Docker Compose launcher with profile support

param(
    [string]$Profiles = "blockchain,sessions,admin",
    [string]$ComposeFile = "compose/docker-compose.yml",
    [switch]$Build = $false,
    [switch]$DetachMode = $true,
    [switch]$Verbose = $false,
    [switch]$Pull = $false
)

$ErrorActionPreference = "Stop"

Write-Host "Starting LUCID RDP Cluster" -ForegroundColor Green
Write-Host "Profiles: $Profiles" -ForegroundColor Yellow

# Verify compose file exists
if (-not (Test-Path $ComposeFile)) {
    Write-Error "Docker Compose file not found: $ComposeFile"
    exit 1
}

# Verify .env file exists
$envFile = "compose/.env"
if (-not (Test-Path $envFile)) {
    Write-Warning ".env file not found: $envFile"
    Write-Host "Copying from .env.example..." -ForegroundColor Yellow
    
    if (Test-Path "compose/.env.example") {
        Copy-Item "compose/.env.example" $envFile
        Write-Host "Please edit $envFile with your configuration" -ForegroundColor Red
        Write-Host "Continuing with defaults..."
    } else {
        Write-Error "No .env.example found. Cannot proceed."
        exit 1
    }
}

# Set Docker Compose environment
$env:COMPOSE_PROFILES = $Profiles
$env:COMPOSE_FILE = $ComposeFile

$composeArgs = @(
    "compose"
    "--file", $ComposeFile
    "--profile", $Profiles.Split(',')
)

# Pull latest images if requested
if ($Pull) {
    Write-Host "Pulling latest images..." -ForegroundColor Cyan
    docker @composeArgs pull
    
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Pull failed, continuing with local images..."
    }
}

# Build services if requested
if ($Build) {
    Write-Host "Building services..." -ForegroundColor Cyan
    $buildArgs = $composeArgs + @("build")
    
    if ($Verbose) {
        $buildArgs += "--progress=plain"
    }
    
    docker @buildArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Build failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

# Start services
Write-Host "Starting cluster services..." -ForegroundColor Cyan
$upArgs = $composeArgs + @("up")

if ($DetachMode) {
    $upArgs += "--detach"
}

if ($Verbose) {
    $upArgs += "--verbose"
}

Write-Host "Running: docker $($upArgs -join ' ')" -ForegroundColor Blue

docker @upArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Cluster startup failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

if ($DetachMode) {
    Write-Host "`nCluster started successfully!" -ForegroundColor Green
    Write-Host "Active profiles: $Profiles" -ForegroundColor Yellow
    
    # Show running services
    Write-Host "`nRunning services:" -ForegroundColor Cyan
    docker compose --file $ComposeFile ps --format "table"
    
    Write-Host "`nUseful commands:" -ForegroundColor Yellow
    Write-Host "  View logs:    docker compose --file $ComposeFile logs -f" -ForegroundColor Blue
    Write-Host "  Stop cluster: docker compose --file $ComposeFile down" -ForegroundColor Blue
    Write-Host "  Service status: docker compose --file $ComposeFile ps" -ForegroundColor Blue
    
    # Show key service URLs
    Write-Host "`nService endpoints:" -ForegroundColor Yellow
    Write-Host "  MongoDB:      mongodb://localhost:27017" -ForegroundColor Blue
    Write-Host "  Blockchain:   http://localhost:8083" -ForegroundColor Blue
    Write-Host "  Sessions:     http://localhost:8084" -ForegroundColor Blue
    Write-Host "  Admin:        http://localhost:8085" -ForegroundColor Blue
    Write-Host "  Tor Proxy:    socks5://localhost:9050" -ForegroundColor Blue
}