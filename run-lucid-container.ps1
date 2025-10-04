# LUCID DEVCONTAINER - DIRECT RUN SCRIPT
# Optimized container execution with proper network, volume, and environment setup

param(
    [switch]$Detached = $false,
    [switch]$Interactive = $true,
    [string]$Command = "/bin/bash"
)

# Configuration
$ContainerName = "lucid-devcontainer-active"
$ImageName = "lucid-devcontainer:latest"
$WorkspaceDir = Get-Location
$NetworkName = "lucid-dev_lucid_net"

Write-Host "[LUCID] Starting optimized devcontainer..." -ForegroundColor Green

# Step 1: Ensure network exists
Write-Host "[LUCID] Checking Docker network..." -ForegroundColor Yellow
try {
    $networkCheck = docker network inspect $NetworkName 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[LUCID] Creating Docker network: $NetworkName" -ForegroundColor Yellow
        docker network create --driver bridge --attachable --subnet=172.20.0.0/16 --gateway=172.20.0.1 --opt com.docker.network.bridge.name=lucid-br0 $NetworkName
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[LUCID] Failed to create network"
            exit 1
        }
    } else {
        Write-Host "[LUCID] Network $NetworkName already exists" -ForegroundColor Green
    }
} catch {
    Write-Error "[LUCID] Network check failed: $_"
    exit 1
}

# Step 2: Remove existing container if it exists
Write-Host "[LUCID] Cleaning up existing container..." -ForegroundColor Yellow
docker rm -f $ContainerName 2>$null

# Step 3: Build run command
$DockerArgs = @(
    "run"
    "--name", $ContainerName
    "--hostname", "lucid-dev"
    "--network", $NetworkName
    
    # Volume mounts
    "--volume", "${WorkspaceDir}:/workspaces/Lucid"
    "--volume", "/var/run/docker.sock:/var/run/docker.sock"
    "--volume", "lucid-devcontainer_buildx_data:/root/.docker/buildx"
    
    # Port forwarding
    "--publish", "2222:2222"
    "--publish", "8080:8080"
    "--publish", "8081:8081"
    "--publish", "9050:9050"
    "--publish", "9051:9051"
    
    # Environment variables
    "--env", "DOCKER_BUILDKIT=1"
    "--env", "DOCKER_DEFAULT_PLATFORM=linux/amd64"
    "--env", "COMPOSE_DOCKER_CLI_BUILD=1"
    "--env", "DOCKER_HOST=unix:///var/run/docker.sock"
    "--env", "PYTHONUNBUFFERED=1"
    "--env", "PYTHONDONTWRITEBYTECODE=1"
    "--env", "LUCID_ENV=dev"
    "--env", "SSH_HOST=pickme@192.168.0.75"
    "--env", "SSH_PORT=22"
    "--env", "LUCID_NETWORK=$NetworkName"
    "--env", "LUCID_BUILDER=lucid-pi"
    
    # Security and capabilities
    "--privileged"
    "--security-opt", "seccomp:unconfined"
    "--cap-add", "SYS_ADMIN"
    "--cap-add", "NET_ADMIN"
    
    # Working directory
    "--workdir", "/workspaces/Lucid"
    
    # Remove container on exit (if not detached)
    if (!$Detached) { "--rm" } else { @() }
    
    # Interactive mode
    if ($Interactive) { "--interactive", "--tty" } else { @() }
    
    # Detached mode
    if ($Detached) { "--detach" } else { @() }
    
    # Image and command
    $ImageName
    $Command
)

# Step 4: Run container
Write-Host "[LUCID] Starting container..." -ForegroundColor Cyan
Write-Host "[LUCID] Workspace mounted from: $WorkspaceDir" -ForegroundColor Yellow
Write-Host "[LUCID] Container will be accessible as: $ContainerName" -ForegroundColor Yellow

try {
    & docker @DockerArgs
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        if ($Detached) {
            Write-Host "[LUCID] Container started successfully in detached mode" -ForegroundColor Green
            Write-Host "[LUCID] Connect with: docker exec -it $ContainerName /bin/bash" -ForegroundColor Cyan
        } else {
            Write-Host "[LUCID] Container session ended" -ForegroundColor Green
        }
    } else {
        Write-Error "[LUCID] Container failed to start (exit code: $exitCode)"
        exit $exitCode
    }
} catch {
    Write-Error "[LUCID] Failed to start container: $_"
    exit 1
}

Write-Host "[LUCID] Done!" -ForegroundColor Green