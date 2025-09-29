# Lucid RDP Windows 11 Deployment Script
# Manages deployment, testing, and operations on Windows 11 development machine
# Target: Raspberry Pi 5 via SSH deployment
# Based on LUCID-STRICT requirements

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet("deploy", "start", "stop", "status", "test", "clean", "ssh-deploy")]
    [string]$Action = "deploy",
    
    [Parameter()]
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev",
    
    [Parameter()]
    [string]$PiHost = "",
    
    [Parameter()]
    [string]$PiUser = "pi",
    
    [Parameter()]
    [switch]$Force,
    
    [Parameter()]
    [switch]$SkipBuild
)

# Runtime variables aligned for Windows 11 and Raspberry Pi 5
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = $SCRIPT_DIR
$BUILD_DIR = Join-Path $PROJECT_ROOT "_build"
$LOG_DIR = Join-Path $PROJECT_ROOT "logs"
$SSH_KEY_PATH = Join-Path $PROJECT_ROOT ".ssh/id_ed25519"

# Environment configuration
$ENV_VARS = @{
    "dev" = @{
        TRON_NETWORK = "shasta"
        LUCID_ENV = "dev"
        MONGO_URL = "mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false"
        BLOCK_RPC_URL = "http://localhost:8545"
        LOG_LEVEL = "DEBUG"
    }
    "prod" = @{
        TRON_NETWORK = "mainnet"
        LUCID_ENV = "prod"
        MONGO_URL = "mongodb://admin:${env:MONGO_PROD_PASSWORD}@lucid_mongo:27017/lucid?authSource=admin&retryWrites=true"
        BLOCK_RPC_URL = "${env:BLOCK_ONION}"
        LOG_LEVEL = "INFO"
    }
}

# Service definitions
$SERVICES = @(
    @{
        Name = "lucid_tor"
        Description = "Tor proxy service"
        Port = 9050
        HealthCheck = "/usr/local/bin/tor-health"
        Priority = 1
    },
    @{
        Name = "lucid_mongo"
        Description = "MongoDB database"
        Port = 27017
        HealthCheck = "mongosh --eval 'db.runCommand({ping:1})'"
        Priority = 2
    },
    @{
        Name = "lucid_api"
        Description = "Main API gateway"
        Port = 8081
        HealthCheck = "curl -f http://localhost:8081/health"
        Priority = 3
    },
    @{
        Name = "lucid_blockchain"
        Description = "Blockchain core service"
        Port = 8082
        HealthCheck = "curl -f http://localhost:8082/health"
        Priority = 4
    }
)

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$ForegroundColor = "White"
    )
    Write-Host $Message -ForegroundColor $ForegroundColor
}

function Test-Prerequisites {
    Write-ColorOutput "Checking prerequisites..." "Blue"
    
    $prereqErrors = @()
    
    # Check Docker
    try {
        docker --version | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[+] Docker is available" "Green"
        } else {
            $prereqErrors += "Docker not working"
        }
    } catch {
        $prereqErrors += "Docker not installed"
    }
    
    # Check Git
    try {
        git --version | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[+] Git is available" "Green"
        } else {
            $prereqErrors += "Git not working"
        }
    } catch {
        $prereqErrors += "Git not installed"
    }
    
    # Check Python
    try {
        python --version | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[+] Python is available" "Green"
        } else {
            $prereqErrors += "Python not working"
        }
    } catch {
        $prereqErrors += "Python not installed"
    }
    
    # Check SSH for Pi deployment
    if ($Action -eq "ssh-deploy" -and $PiHost) {
        try {
            if (Test-Path $SSH_KEY_PATH) {
                Write-ColorOutput "[+] SSH key found" "Green"
            } else {
                $prereqErrors += "SSH key not found: $SSH_KEY_PATH"
            }
        } catch {
            $prereqErrors += "SSH key check failed"
        }
    }
    
    if ($prereqErrors.Count -gt 0) {
        Write-ColorOutput "Prerequisites check failed:" "Red"
        foreach ($error in $prereqErrors) {
            Write-ColorOutput "  - $error" "Red"
        }
        return $false
    }
    
    Write-ColorOutput "[+] All prerequisites met" "Green"
    return $true
}

function Initialize-Environment {
    Write-ColorOutput "Initializing environment: $Environment" "Blue"
    
    # Create directories
    @($BUILD_DIR, $LOG_DIR) | ForEach-Object {
        if (-not (Test-Path $_)) {
            New-Item -ItemType Directory -Path $_ -Force | Out-Null
            Write-ColorOutput "[+] Created directory: $_" "Green"
        }
    }
    
    # Set environment variables
    $envConfig = $ENV_VARS[$Environment]
    foreach ($key in $envConfig.Keys) {
        $value = $envConfig[$key]
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
        Write-ColorOutput "[+] Set $key=$value" "Green"
    }
    
    # Initialize networks
    Write-ColorOutput "Creating Docker networks..." "Yellow"
    & "$SCRIPT_DIR/06-orchestration-runtime/net/setup_lucid_networks.ps1" -Action create -Environment $Environment
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "[-] Network setup failed" "Red"
        return $false
    }
    
    return $true
}

function Build-Images {
    if ($SkipBuild) {
        Write-ColorOutput "[!] Skipping build as requested" "Yellow"
        return $true
    }
    
    Write-ColorOutput "Building Docker images..." "Blue"
    
    try {
        # Build development container
        & "$SCRIPT_DIR/build-devcontainer.ps1" -TestOnly
        
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "[-] DevContainer build failed" "Red"
            return $false
        }
        
        Write-ColorOutput "[+] Images built successfully" "Green"
        return $true
        
    } catch {
        Write-ColorOutput "[-] Build process failed: $_" "Red"
        return $false
    }
}

function Start-Services {
    Write-ColorOutput "Starting Lucid services..." "Blue"
    
    try {
        # Start services using docker-compose
        docker-compose -f "_compose_resolved.yaml" --profile dev up -d
        
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "[-] Service startup failed" "Red"
            return $false
        }
        
        # Wait for services to be healthy
        Write-ColorOutput "Waiting for services to be healthy..." "Yellow"
        Start-Sleep -Seconds 10
        
        # Check service health
        $healthyServices = 0
        foreach ($service in $SERVICES) {
            $isHealthy = Test-ServiceHealth -ServiceName $service.Name -Port $service.Port -HealthCheck $service.HealthCheck
            if ($isHealthy) {
                Write-ColorOutput "[+] $($service.Name) is healthy" "Green"
                $healthyServices++
            } else {
                Write-ColorOutput "[-] $($service.Name) is unhealthy" "Red"
            }
        }
        
        if ($healthyServices -eq $SERVICES.Count) {
            Write-ColorOutput "[+] All services started successfully" "Green"
            return $true
        } else {
            Write-ColorOutput "[-] $($SERVICES.Count - $healthyServices) services failed to start" "Red"
            return $false
        }
        
    } catch {
        Write-ColorOutput "[-] Service startup error: $_" "Red"
        return $false
    }
}

function Stop-Services {
    Write-ColorOutput "Stopping Lucid services..." "Blue"
    
    try {
        docker-compose -f "_compose_resolved.yaml" --profile dev down
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[+] Services stopped successfully" "Green"
            return $true
        } else {
            Write-ColorOutput "[-] Service stop failed" "Red"
            return $false
        }
        
    } catch {
        Write-ColorOutput "[-] Service stop error: $_" "Red"
        return $false
    }
}

function Test-ServiceHealth {
    param(
        [string]$ServiceName,
        [int]$Port,
        [string]$HealthCheck
    )
    
    try {
        # Check if container is running
        $containerStatus = docker ps --filter "name=$ServiceName" --format "{{.Status}}"
        if (-not $containerStatus -or $containerStatus -notmatch "Up") {
            return $false
        }
        
        # Test port connectivity
        $connection = Test-NetConnection -ComputerName localhost -Port $Port -InformationLevel Quiet
        if (-not $connection) {
            return $false
        }
        
        # Run health check inside container if provided
        if ($HealthCheck -and $HealthCheck -notmatch "^curl") {
            docker exec $ServiceName $HealthCheck.Split(' ') | Out-Null
            return $LASTEXITCODE -eq 0
        }
        
        return $true
        
    } catch {
        return $false
    }
}

function Show-ServiceStatus {
    Write-ColorOutput "===== Lucid Service Status =====" "Cyan"
    
    # Show Docker containers
    Write-ColorOutput "Docker Containers:" "Yellow"
    docker ps --filter "label=lucid" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    Write-Host ""
    
    # Show Docker networks
    Write-ColorOutput "Docker Networks:" "Yellow"
    docker network ls --filter "label=lucid.network.purpose" --format "table {{.Name}}\t{{.Driver}}\t{{.Labels}}"
    
    Write-Host ""
    
    # Test service health
    Write-ColorOutput "Service Health:" "Yellow"
    foreach ($service in $SERVICES) {
        $isHealthy = Test-ServiceHealth -ServiceName $service.Name -Port $service.Port -HealthCheck $service.HealthCheck
        $status = if ($isHealthy) { "[+] HEALTHY" } else { "[-] UNHEALTHY" }
        $color = if ($isHealthy) { "Green" } else { "Red" }
        
        Write-ColorOutput "  $($service.Name): $status" $color
    }
    
    Write-Host ""
    
    # Show environment info
    Write-ColorOutput "Environment: $Environment" "Yellow"
    Write-ColorOutput "TRON Network: $env:TRON_NETWORK" "White"
    Write-ColorOutput "Lucid Env: $env:LUCID_ENV" "White"
    Write-ColorOutput "Log Level: $env:LOG_LEVEL" "White"
}

function Test-Deployment {
    Write-ColorOutput "Testing deployment..." "Blue"
    
    $testResults = @()
    
    # Test 1: Network connectivity
    Write-ColorOutput "Testing network connectivity..." "Yellow"
    try {
        & "$SCRIPT_DIR/06-orchestration-runtime/net/setup_lucid_networks.ps1" -Action test
        $testResults += @{Test = "Network Connectivity"; Result = ($LASTEXITCODE -eq 0)}
    } catch {
        $testResults += @{Test = "Network Connectivity"; Result = $false}
    }
    
    # Test 2: API Gateway health
    Write-ColorOutput "Testing API Gateway..." "Yellow"
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8081/health" -TimeoutSec 5
        $testResults += @{Test = "API Gateway"; Result = ($response -ne $null)}
    } catch {
        $testResults += @{Test = "API Gateway"; Result = $false}
    }
    
    # Test 3: Blockchain service health
    Write-ColorOutput "Testing Blockchain service..." "Yellow"
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8082/health" -TimeoutSec 5
        $testResults += @{Test = "Blockchain Service"; Result = ($response -ne $null)}
    } catch {
        $testResults += @{Test = "Blockchain Service"; Result = $false}
    }
    
    # Test 4: Database connectivity
    Write-ColorOutput "Testing database connectivity..." "Yellow"
    try {
        docker exec lucid_mongo mongosh --quiet --eval "db.runCommand({ping:1})" | Out-Null
        $testResults += @{Test = "Database"; Result = ($LASTEXITCODE -eq 0)}
    } catch {
        $testResults += @{Test = "Database"; Result = $false}
    }
    
    # Test 5: Tor proxy
    Write-ColorOutput "Testing Tor proxy..." "Yellow"
    try {
        docker exec lucid_tor curl -f --socks5 127.0.0.1:9050 http://check.torproject.org/ | Out-Null
        $testResults += @{Test = "Tor Proxy"; Result = ($LASTEXITCODE -eq 0)}
    } catch {
        $testResults += @{Test = "Tor Proxy"; Result = $false}
    }
    
    # Summary
    Write-ColorOutput "===== Test Results =====" "Cyan"
    $passed = 0
    foreach ($result in $testResults) {
        $status = if ($result.Result) { "PASS" } else { "FAIL" }
        $color = if ($result.Result) { "Green" } else { "Red" }
        Write-ColorOutput "  $($result.Test): $status" $color
        if ($result.Result) { $passed++ }
    }
    
    $total = $testResults.Count
    Write-ColorOutput "===== $passed/$total tests passed =====" "Cyan"
    
    return $passed -eq $total
}

function Deploy-ToPi {
    if (-not $PiHost) {
        Write-ColorOutput "[-] Pi host not specified. Use -PiHost parameter" "Red"
        return $false
    }
    
    Write-ColorOutput "Deploying to Raspberry Pi: $PiUser@$PiHost" "Blue"
    
    try {
        # Test SSH connectivity
        Write-ColorOutput "Testing SSH connection..." "Yellow"
        ssh -i $SSH_KEY_PATH -o ConnectTimeout=5 "$PiUser@$PiHost" "echo 'SSH connection successful'"
        
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "[-] SSH connection failed" "Red"
            return $false
        }
        
        # Create remote directories
        Write-ColorOutput "Creating remote directories..." "Yellow"
        ssh -i $SSH_KEY_PATH "$PiUser@$PiHost" "mkdir -p ~/lucid/{data,logs,config}"
        
        # Copy project files
        Write-ColorOutput "Copying project files..." "Yellow"
        scp -i $SSH_KEY_PATH -r ./_compose_resolved.yaml "$PiUser@$PiHost:~/lucid/"
        scp -i $SSH_KEY_PATH -r ./06-orchestration-runtime "$PiUser@$PiHost:~/lucid/"
        scp -i $SSH_KEY_PATH -r "./deploy-lucid-pi.sh" "$PiUser@$PiHost:~/lucid/"
        
        # Execute remote deployment
        Write-ColorOutput "Executing remote deployment..." "Yellow"
        ssh -i $SSH_KEY_PATH "$PiUser@$PiHost" "cd ~/lucid && chmod +x deploy-lucid-pi.sh && ./deploy-lucid-pi.sh deploy $Environment"
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[+] Pi deployment completed successfully" "Green"
            return $true
        } else {
            Write-ColorOutput "[-] Pi deployment failed" "Red"
            return $false
        }
        
    } catch {
        Write-ColorOutput "[-] Pi deployment error: $_" "Red"
        return $false
    }
}

function Clean-Deployment {
    Write-ColorOutput "Cleaning deployment..." "Blue"
    
    try {
        # Stop services
        Stop-Services
        
        # Remove containers
        Write-ColorOutput "Removing containers..." "Yellow"
        docker system prune -f --volumes
        
        # Remove networks
        Write-ColorOutput "Removing networks..." "Yellow"
        & "$SCRIPT_DIR/06-orchestration-runtime/net/setup_lucid_networks.ps1" -Action remove
        
        # Clean build directory
        if (Test-Path $BUILD_DIR) {
            Remove-Item -Recurse -Force $BUILD_DIR
            Write-ColorOutput "[+] Cleaned build directory" "Green"
        }
        
        Write-ColorOutput "[+] Cleanup completed" "Green"
        return $true
        
    } catch {
        Write-ColorOutput "[-] Cleanup error: $_" "Red"
        return $false
    }
}

# Main execution
Write-ColorOutput "===== Lucid RDP Windows 11 Deployment =====" "Cyan"
Write-ColorOutput "Action: $Action" "Yellow"
Write-ColorOutput "Environment: $Environment" "Yellow"
if ($PiHost) { Write-ColorOutput "Pi Target: $PiUser@$PiHost" "Yellow" }
Write-Host ""

# Check prerequisites
if (-not (Test-Prerequisites)) {
    Write-ColorOutput "Prerequisites not met, aborting" "Red"
    exit 1
}

# Execute action
$success = $false

switch ($Action) {
    "deploy" {
        if ((Initialize-Environment) -and (Build-Images) -and (Start-Services)) {
            $success = Test-Deployment
        }
    }
    
    "start" {
        if (Initialize-Environment) {
            $success = Start-Services
        }
    }
    
    "stop" {
        $success = Stop-Services
    }
    
    "status" {
        Show-ServiceStatus
        $success = $true
    }
    
    "test" {
        $success = Test-Deployment
    }
    
    "clean" {
        $success = Clean-Deployment
    }
    
    "ssh-deploy" {
        if ((Initialize-Environment) -and (Build-Images)) {
            $success = Deploy-ToPi
        }
    }
}

# Summary
Write-Host ""
if ($success) {
    Write-ColorOutput "===== $Action completed successfully =====" "Green"
    exit 0
} else {
    Write-ColorOutput "===== $Action failed =====" "Red"
    exit 1
}