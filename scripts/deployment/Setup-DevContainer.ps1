# Lucid Development Container Setup - Windows PowerShell Edition
# Complete setup for Docker Desktop post-reinstall with SSH configuration
# Addresses Docker-in-Docker, buildx, and network requirements

param(
    [switch]$Clean = $false,
    [switch]$Setup = $false,
    [switch]$Build = $false,
    [switch]$Test = $false,
    [switch]$All = $false
)

# Set error handling
$ErrorActionPreference = "Stop"

# If no specific action, run all phases
if (-not ($Clean -or $Setup -or $Build -or $Test) -or $All) {
    $Clean = $true
    $Setup = $true  
    $Build = $true
    $Test = $true
}

# Configuration
$NetworkName = "lucid-dev_lucid_net"
$BuilderName = "lucid-pi"
$ComposeFile = ".devcontainer/docker-compose.dev.yml"
$ContainerName = "lucid-devcontainer"

# Logging functions
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        "INFO" { "Blue" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

# Check Docker Desktop status
function Test-DockerDesktop {
    Write-Log "Checking Docker Desktop status..."
    
    try {
        $null = docker info 2>$null
        Write-Log "Docker Desktop is running" "SUCCESS"
        return $true
    }
    catch {
        Write-Log "Docker Desktop is not running or not accessible" "ERROR"
        return $false
    }
}

# Wait for Docker Desktop to be ready
function Wait-ForDockerDesktop {
    Write-Log "Waiting for Docker Desktop to be ready..."
    
    $maxAttempts = 30
    $attempt = 0
    
    do {
        $attempt++
        if (Test-DockerDesktop) {
            Write-Log "Docker Desktop is ready" "SUCCESS"
            return $true
        }
        
        Write-Log "Attempt $attempt/$maxAttempts - Docker Desktop not ready, waiting 5 seconds..."
        Start-Sleep -Seconds 5
    } while ($attempt -lt $maxAttempts)
    
    Write-Log "Docker Desktop failed to become ready after $maxAttempts attempts" "ERROR"
    return $false
}

# PHASE 1: CLEAN
function Invoke-CleanPhase {
    if (-not $Clean) { return }
    
    Write-Log "=== PHASE 1: CLEANING ENVIRONMENT ===" "INFO"
    
    if (-not (Wait-ForDockerDesktop)) {
        throw "Docker Desktop is not available"
    }
    
    # Stop and remove existing containers
    Write-Log "Stopping and removing existing Lucid containers..."
    try {
        $containers = docker ps -aq --filter "name=lucid"
        if ($containers) {
            docker stop $containers 2>$null
            docker rm -f $containers 2>$null
            Write-Log "Cleaned up existing containers" "SUCCESS"
        }
    }
    catch {
        Write-Log "No existing containers to clean" "INFO"
    }
    
    # Remove existing images
    Write-Log "Removing existing Lucid images..."
    try {
        $images = docker images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -match "(lucid|pickme)" }
        if ($images) {
            foreach ($image in $images) {
                docker rmi -f $image 2>$null
            }
            Write-Log "Cleaned up existing images" "SUCCESS"
        }
    }
    catch {
        Write-Log "No existing images to clean" "INFO"
    }
    
    # Clean buildx cache and builder
    Write-Log "Cleaning buildx cache and builder..."
    try {
        docker buildx prune --all --force 2>$null
        docker buildx rm $BuilderName --force 2>$null
        Write-Log "Cleaned buildx cache and builder" "SUCCESS"
    }
    catch {
        Write-Log "Buildx cleanup completed" "INFO"
    }
    
    Write-Log "=== PHASE 1 COMPLETED: ENVIRONMENT CLEANED ===" "SUCCESS"
}

# PHASE 2: SETUP
function Invoke-SetupPhase {
    if (-not $Setup) { return }
    
    Write-Log "=== PHASE 2: SETTING UP ENVIRONMENT ===" "INFO"
    
    if (-not (Wait-ForDockerDesktop)) {
        throw "Docker Desktop is not available"
    }
    
    # Create SSH directory and configuration
    Write-Log "Setting up SSH configuration..."
    $sshDir = "$env:USERPROFILE\.ssh"
    if (-not (Test-Path $sshDir)) {
        New-Item -Path $sshDir -ItemType Directory -Force | Out-Null
        Write-Log "Created SSH directory: $sshDir" "SUCCESS"
    }
    
    # Create SSH config if it doesn't exist
    $sshConfig = Join-Path $sshDir "config"
    if (-not (Test-Path $sshConfig)) {
        @"
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile=nul
    LogLevel ERROR
    ServerAliveInterval 60
    ServerAliveCountMax 3

Host lucid-pi
    HostName 192.168.0.75
    User pickme
    Port 22
    ForwardAgent yes
"@ | Out-File -FilePath $sshConfig -Encoding UTF8
        Write-Log "Created SSH config: $sshConfig" "SUCCESS"
    }
    
    # Create .gitconfig if it doesn't exist
    $gitConfig = "$env:USERPROFILE\.gitconfig"
    if (-not (Test-Path $gitConfig)) {
        @"
[user]
    name = Lucid Developer
    email = dev@lucid.local
[core]
    autocrlf = input
    filemode = false
[pull]
    rebase = false
"@ | Out-File -FilePath $gitConfig -Encoding UTF8
        Write-Log "Created Git config: $gitConfig" "SUCCESS"
    }
    
    # Create Docker network
    Write-Log "Creating Docker network: $NetworkName"
    try {
        docker network create $NetworkName --driver bridge --attachable 2>$null
        Write-Log "Created Docker network: $NetworkName" "SUCCESS"
    }
    catch {
        Write-Log "Docker network already exists or created: $NetworkName" "INFO"
    }
    
    # Create buildx builder
    Write-Log "Creating buildx builder: $BuilderName"
    try {
        docker buildx create --name $BuilderName --driver docker-container --platform linux/amd64,linux/arm64 --use --bootstrap
        Write-Log "Created buildx builder: $BuilderName" "SUCCESS"
    }
    catch {
        Write-Log "Failed to create buildx builder, using default" "WARN"
    }
    
    # Create required volumes
    Write-Log "Creating required Docker volumes..."
    $volumes = @(
        "lucid-dev_onion_state",
        "lucid-dev_docker_data",
        "lucid-devcontainer_docker_data"
    )
    
    foreach ($volume in $volumes) {
        try {
            docker volume create $volume 2>$null
            Write-Log "Created volume: $volume" "SUCCESS"
        }
        catch {
            Write-Log "Volume already exists: $volume" "INFO"
        }
    }
    
    # Verify Docker system status
    Write-Log "Docker system status:"
    docker system df
    docker network ls | Where-Object { $_ -match "lucid" }
    
    Write-Log "=== PHASE 2 COMPLETED: ENVIRONMENT SETUP ===" "SUCCESS"
}

# PHASE 3: BUILD
function Invoke-BuildPhase {
    if (-not $Build) { return }
    
    Write-Log "=== PHASE 3: BUILDING CONTAINERS ===" "INFO"
    
    if (-not (Wait-ForDockerDesktop)) {
        throw "Docker Desktop is not available"
    }
    
    # Set environment variables for build
    $env:DOCKER_BUILDKIT = "1"
    $env:COMPOSE_DOCKER_CLI_BUILD = "1"
    
    # Build the development container
    Write-Log "Building development container with Docker-in-Docker support..."
    try {
        docker-compose -f $ComposeFile build --no-cache
        Write-Log "Successfully built development container" "SUCCESS"
    }
    catch {
        Write-Log "Build failed, attempting alternative method..." "WARN"
        
        # Fallback: Build Dockerfile directly
        docker build -f .devcontainer/Dockerfile -t pickme/lucid:dev-dind .
        Write-Log "Fallback build completed" "SUCCESS"
    }
    
    # List built images
    Write-Log "Built images:"
    docker images | Where-Object { $_ -match "(lucid|pickme)" }
    
    Write-Log "=== PHASE 3 COMPLETED: CONTAINERS BUILT ===" "SUCCESS"
}

# PHASE 4: TEST
function Invoke-TestPhase {
    if (-not $Test) { return }
    
    Write-Log "=== PHASE 4: TESTING SYSTEM ===" "INFO"
    
    if (-not (Wait-ForDockerDesktop)) {
        throw "Docker Desktop is not available"
    }
    
    # Start the development container
    Write-Log "Starting development container for testing..."
    try {
        docker-compose -f $ComposeFile up -d
        Write-Log "Development container started" "SUCCESS"
        
        # Wait for container to be ready
        Write-Log "Waiting for container to be ready..."
        Start-Sleep -Seconds 30
        
        # Test Docker-in-Docker functionality
        Write-Log "Testing Docker-in-Docker functionality..."
        $dockerVersion = docker exec $ContainerName docker --version 2>$null
        if ($dockerVersion) {
            Write-Log "Docker available inside container: $dockerVersion" "SUCCESS"
            
            # Test container creation
            Write-Log "Testing container creation capability..."
            $testResult = docker exec $ContainerName docker run --rm hello-world 2>$null
            if ($testResult -match "Hello from Docker") {
                Write-Log "Container creation test PASSED" "SUCCESS"
            } else {
                Write-Log "Container creation test FAILED" "ERROR"
            }
        } else {
            Write-Log "Docker not available inside container" "ERROR"
        }
        
        # Test SSH access
        Write-Log "Testing SSH configuration..."
        $sshTest = docker exec $ContainerName test -f /root/.ssh/config
        if ($LASTEXITCODE -eq 0) {
            Write-Log "SSH configuration present" "SUCCESS"
        } else {
            Write-Log "SSH configuration missing" "WARN"
        }
        
        # Test Java
        Write-Log "Testing Java availability..."
        $javaVersion = docker exec $ContainerName java -version 2>&1
        if ($javaVersion -match "openjdk") {
            Write-Log "Java available: $($javaVersion[0])" "SUCCESS"
        } else {
            Write-Log "Java not available" "ERROR"
        }
        
        # Test Python
        Write-Log "Testing Python availability..."
        $pythonVersion = docker exec $ContainerName python3 --version 2>$null
        if ($pythonVersion) {
            Write-Log "Python available: $pythonVersion" "SUCCESS"
        } else {
            Write-Log "Python not available" "ERROR"
        }
        
        # Show container status
        Write-Log "Container status:"
        docker-compose -f $ComposeFile ps
        
        Write-Log "=== PHASE 4 COMPLETED: SYSTEM TESTED ===" "SUCCESS"
        
    } catch {
        Write-Log "Test phase failed: $($_.Exception.Message)" "ERROR"
        
        # Show logs for debugging
        Write-Log "Container logs:"
        docker-compose -f $ComposeFile logs --tail=20
    }
}

# Main execution
function Main {
    Write-Log "=== LUCID DEVELOPMENT CONTAINER SETUP ===" "INFO"
    Write-Log "Configuration: Network=$NetworkName, Builder=$BuilderName" "INFO"
    
    # Verify we're in the correct directory
    if (-not (Test-Path $ComposeFile)) {
        Write-Log "Compose file not found: $ComposeFile" "ERROR"
        Write-Log "Please run this script from the Lucid project root directory" "ERROR"
        exit 1
    }
    
    try {
        # Execute phases
        Invoke-CleanPhase
        Invoke-SetupPhase
        Invoke-BuildPhase
        Invoke-TestPhase
        
        # Final instructions
        Write-Log "=== SETUP COMPLETED SUCCESSFULLY ===" "SUCCESS"
        Write-Host ""
        Write-Log "Next steps:" "INFO"
        Write-Host "  1. Open VS Code in this directory" -ForegroundColor Cyan
        Write-Host "  2. Install 'Dev Containers' extension if not installed" -ForegroundColor Cyan
        Write-Host "  3. Press Ctrl+Shift+P and select 'Dev Containers: Reopen in Container'" -ForegroundColor Cyan
        Write-Host "  4. VS Code will attach to the running dev container" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Direct access methods:" -ForegroundColor Yellow
        Write-Host "  • SSH: ssh -p 2222 root@localhost" -ForegroundColor White
        Write-Host "  • Docker exec: docker exec -it lucid-devcontainer bash" -ForegroundColor White
        Write-Host ""
        Write-Host "Inside container features:" -ForegroundColor Green
        Write-Host "  • Docker-in-Docker enabled" -ForegroundColor White
        Write-Host "  • Java 17 with Maven/Gradle" -ForegroundColor White  
        Write-Host "  • Python 3 with crypto libraries" -ForegroundColor White
        Write-Host "  • Tor proxy (SOCKS: 9050, Control: 9051)" -ForegroundColor White
        Write-Host "  • Build tools and SSH configured" -ForegroundColor White
        
    } catch {
        Write-Log "Setup failed: $($_.Exception.Message)" "ERROR"
        exit 1
    }
}

# Execute main function
Main