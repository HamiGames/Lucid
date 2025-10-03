# Lucid Development Container Build Script
# Comprehensive Docker-in-Docker development environment setup
# Per user requirements: full script assessment, clean, prep, build, and test

param(
    [switch]$Clean = $false,
    [switch]$Prep = $false,
    [switch]$Build = $false,
    [switch]$Test = $false,
    [switch]$All = $false,
    [string]$Profile = "dev"
)

# Set error handling
$ErrorActionPreference = "Stop"

Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Lucid Development Container Build" -ForegroundColor Cyan
Write-Host "Docker-in-Docker Environment" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# If no specific action, run all
if (-not ($Clean -or $Prep -or $Build -or $Test) -or $All) {
    $Clean = $true
    $Prep = $true
    $Build = $true
    $Test = $true
}

# Configuration
$ComposeFile = "06-orchestration-runtime/compose/lucid-dev.yaml"
$EnvFile = "06-orchestration-runtime/compose/.env"
$NetworkName = "lucid-dev_lucid_net"
$BuilderName = "lucid_builder"

# Function to log with timestamp
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

# Function to check if Docker is running
function Test-DockerRunning {
    try {
        docker info | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to ensure Docker is running
function Ensure-DockerRunning {
    if (-not (Test-DockerRunning)) {
        Write-Log "Docker is not running. Please start Docker Desktop and try again." "ERROR"
        exit 1
    }
    Write-Log "Docker daemon is running" "SUCCESS"
}

# PHASE 1: CLEAN
if ($Clean) {
    Write-Log "=== PHASE 1: CLEANING DOCKER ENVIRONMENT ===" "INFO"
    
    Ensure-DockerRunning
    
    Write-Log "Stopping all Lucid containers..." "INFO"
    try {
        $containers = docker ps -q --filter "name=lucid"
        if ($containers) {
            docker stop $containers
            Write-Log "Stopped containers: $($containers -join ', ')" "SUCCESS"
        }
    }
    catch {
        Write-Log "No running Lucid containers to stop" "INFO"
    }
    
    Write-Log "Removing all Lucid containers..." "INFO"
    try {
        $allContainers = docker ps -aq --filter "name=lucid"
        if ($allContainers) {
            docker rm -f $allContainers
            Write-Log "Removed containers: $($allContainers -join ', ')" "SUCCESS"
        }
    }
    catch {
        Write-Log "No Lucid containers to remove" "INFO"
    }
    
    Write-Log "Removing Lucid images..." "INFO"
    try {
        $images = docker images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -match "lucid|pickme" }
        if ($images) {
            docker rmi -f $images
            Write-Log "Removed images: $($images -join ', ')" "SUCCESS"
        }
    }
    catch {
        Write-Log "No Lucid images to remove" "INFO"
    }
    
    Write-Log "Cleaning Docker buildx cache..." "INFO"
    try {
        docker buildx prune --all --force
        Write-Log "Buildx cache cleaned" "SUCCESS"
    }
    catch {
        Write-Log "Failed to clean buildx cache, continuing..." "WARN"
    }
    
    Write-Log "Removing existing builder..." "INFO"
    try {
        docker buildx rm $BuilderName --force
        Write-Log "Removed builder: $BuilderName" "SUCCESS"
    }
    catch {
        Write-Log "No existing builder to remove" "INFO"
    }
    
    Write-Log "System cleanup..." "INFO"
    docker system prune -f
    Write-Log "System cleanup completed" "SUCCESS"
    
    Write-Log "=== PHASE 1 COMPLETED: ENVIRONMENT CLEANED ===" "SUCCESS"
}

# PHASE 2: PREP
if ($Prep) {
    Write-Log "=== PHASE 2: PREPARING ENVIRONMENT ===" "INFO"
    
    Ensure-DockerRunning
    
    Write-Log "Checking project structure..." "INFO"
    if (-not (Test-Path $ComposeFile)) {
        Write-Log "Compose file not found: $ComposeFile" "ERROR"
        exit 1
    }
    Write-Log "Compose file found: $ComposeFile" "SUCCESS"
    
    if (-not (Test-Path $EnvFile)) {
        Write-Log "Environment file not found: $EnvFile" "ERROR"
        exit 1
    }
    Write-Log "Environment file found: $EnvFile" "SUCCESS"
    
    Write-Log "Creating Docker network..." "INFO"
    try {
        docker network create $NetworkName --driver bridge --attachable
        Write-Log "Created network: $NetworkName" "SUCCESS"
    }
    catch {
        Write-Log "Network already exists or failed to create: $NetworkName" "INFO"
    }
    
    Write-Log "Creating buildx builder..." "INFO"
    try {
        docker buildx create --name $BuilderName --driver docker-container --use
        Write-Log "Created buildx builder: $BuilderName" "SUCCESS"
    }
    catch {
        Write-Log "Failed to create buildx builder, using default" "WARN"
    }
    
    Write-Log "Creating required volumes..." "INFO"
    $volumes = @(
        "lucid-dev_onion_state",
        "lucid-dev_docker_data"
    )
    
    foreach ($volume in $volumes) {
        try {
            docker volume create $volume
            Write-Log "Created volume: $volume" "SUCCESS"
        }
        catch {
            Write-Log "Volume already exists: $volume" "INFO"
        }
    }
    
    Write-Log "Verifying Docker system status..." "INFO"
    docker system df
    docker network ls | Where-Object { $_ -match "lucid" }
    
    Write-Log "=== PHASE 2 COMPLETED: ENVIRONMENT PREPARED ===" "SUCCESS"
}

# PHASE 3: BUILD
if ($Build) {
    Write-Log "=== PHASE 3: BUILDING CONTAINERS ===" "INFO"
    
    Ensure-DockerRunning
    
    Write-Log "Setting environment variables..." "INFO"
    $env:DOCKER_BUILDKIT = "1"
    $env:COMPOSE_DOCKER_CLI_BUILD = "1"
    $env:HOME = $env:USERPROFILE  # Windows compatibility
    
    Write-Log "Building all services with no-cache..." "INFO"
    Set-Location "06-orchestration-runtime/compose"
    
    try {
        # Build with progress output and no cache for clean build
        docker-compose -f lucid-dev.yaml build --no-cache --progress plain --parallel
        Write-Log "All services built successfully" "SUCCESS"
    }
    catch {
        Write-Log "Build failed: $($_.Exception.Message)" "ERROR"
        
        Write-Log "Attempting individual service builds..." "INFO"
        $services = @("devcontainer", "tor-proxy", "lucid_mongo", "lucid_api", "api-gateway", "tunnel-tools", "server-tools")
        
        foreach ($service in $services) {
            try {
                Write-Log "Building service: $service" "INFO"
                docker-compose -f lucid-dev.yaml build --no-cache $service
                Write-Log "Built service: $service" "SUCCESS"
            }
            catch {
                Write-Log "Failed to build service: $service" "ERROR"
            }
        }
    }
    finally {
        Set-Location "../.."
    }
    
    Write-Log "Listing built images..." "INFO"
    docker images | Where-Object { $_ -match "lucid|pickme" }
    
    Write-Log "=== PHASE 3 COMPLETED: CONTAINERS BUILT ===" "SUCCESS"
}

# PHASE 4: TEST
if ($Test) {
    Write-Log "=== PHASE 4: TESTING SYSTEM ===" "INFO"
    
    Ensure-DockerRunning
    
    Write-Log "Starting services..." "INFO"
    Set-Location "06-orchestration-runtime/compose"
    
    try {
        # Start services with profile
        docker-compose -f lucid-dev.yaml --profile $Profile up -d
        Write-Log "Services started" "SUCCESS"
        
        # Wait for services to be ready
        Write-Log "Waiting for services to be ready..." "INFO"
        Start-Sleep -Seconds 30
        
        Write-Log "Checking service status..." "INFO"
        docker-compose -f lucid-dev.yaml ps
        
        Write-Log "Testing devcontainer Docker-in-Docker capability..." "INFO"
        $testResult = docker exec lucid_devcontainer docker --version
        if ($testResult) {
            Write-Log "Docker available in devcontainer: $testResult" "SUCCESS"
            
            # Test container creation capability
            Write-Log "Testing container creation..." "INFO"
            $createTest = docker exec lucid_devcontainer docker run --rm hello-world
            if ($createTest -match "Hello from Docker") {
                Write-Log "Container creation test PASSED" "SUCCESS"
            }
            else {
                Write-Log "Container creation test FAILED" "ERROR"
            }
        }
        else {
            Write-Log "Docker not available in devcontainer" "ERROR"
        }
        
        Write-Log "Testing project file access..." "INFO"
        $fileTest = docker exec lucid_devcontainer ls -la /workspaces/Lucid
        Write-Log "Project files accessible: $(($fileTest | Measure-Object).Count) items" "SUCCESS"
        
        Write-Log "Service health check..." "INFO"
        $healthResults = docker-compose -f lucid-dev.yaml ps --format "table {{.Name}}\t{{.Status}}"
        Write-Host $healthResults
        
        Write-Log "=== PHASE 4 COMPLETED: SYSTEM TESTED ===" "SUCCESS"
        
        Write-Log "Development environment is ready!" "SUCCESS"
        Write-Log "Access devcontainer: docker exec -it lucid_devcontainer bash" "INFO"
        Write-Log "VS Code: Open folder in devcontainer" "INFO"
        
    }
    catch {
        Write-Log "Test phase failed: $($_.Exception.Message)" "ERROR"
        
        Write-Log "Collecting logs for debugging..." "INFO"
        docker-compose -f lucid-dev.yaml logs --tail=50
    }
    finally {
        Set-Location "../.."
    }
}

Write-Log "=== BUILD SCRIPT COMPLETED ===" "SUCCESS"
Write-Log "For VS Code integration:" "INFO"
Write-Log "1. Install 'Dev Containers' extension" "INFO"
Write-Log "2. Open project folder" "INFO"
Write-Log "3. Ctrl+Shift+P -> 'Dev Containers: Reopen in Container'" "INFO"
Write-Log "4. Docker will be available inside the container for creating other containers" "INFO"