# LUCID DISTROLESS CLUSTER DEPLOYMENT
# Complete deployment script for Lucid distroless cluster
# Builds images, generates configurations, and deploys the cluster

param(
    [switch]$Build = $true,
    [switch]$Push = $false,
    [switch]$Deploy = $true,
    [switch]$GenerateConfig = $true,
    [switch]$Force = $false,
    [switch]$Verbose = $false,
    [string]$Registry = "pickme",
    [string]$Repository = "lucid",
    [string]$Tag = "latest",
    [string]$Environment = "production",
    [string]$ComposeFile = "infrastructure/compose/lucid-distroless-complete.yaml"
)

# Set strict mode and error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Color functions for output
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success { param([string]$Message) Write-ColorOutput "✅ $Message" "Green" }
function Write-Error { param([string]$Message) Write-ColorOutput "❌ $Message" "Red" }
function Write-Warning { param([string]$Message) Write-ColorOutput "⚠️ $Message" "Yellow" }
function Write-Info { param([string]$Message) Write-ColorOutput "ℹ️ $Message" "Cyan" }
function Write-Progress { param([string]$Message) Write-ColorOutput "🔄 $Message" "Blue" }

# Global variables
$script:DeploymentResults = @{}
$script:StartTime = Get-Date

function Test-Prerequisites {
    Write-Progress "Testing deployment prerequisites..."
    
    $prerequisites = @(
        @{ Name = "Docker"; Command = "docker"; Version = "--version" }
        @{ Name = "Docker Compose"; Command = "docker-compose"; Version = "--version" }
        @{ Name = "Git"; Command = "git"; Version = "--version" }
        @{ Name = "PowerShell"; Command = "powershell"; Version = "-Version" }
    )
    
    foreach ($prereq in $prerequisites) {
        try {
            $output = & $prereq.Command $prereq.Version 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Success "$($prereq.Name): Available"
            } else {
                throw "Command failed"
            }
        }
        catch {
            Write-Error "$($prereq.Name): Not available or not working"
            throw "$($prereq.Name) is required but not available"
        }
    }
    
    # Test Docker daemon
    try {
        docker ps | Out-Null
        Write-Success "Docker daemon: Running"
    }
    catch {
        Write-Error "Docker daemon: Not running or not accessible"
        throw "Docker daemon must be running"
    }
    
    # Test Docker Hub connectivity (if pushing)
    if ($Push) {
        try {
            docker pull hello-world | Out-Null
            docker rmi hello-world | Out-Null
            Write-Success "Docker Hub: Accessible"
        }
        catch {
            Write-Warning "Docker Hub: May not be accessible (will attempt push anyway)"
        }
    }
    
    Write-Success "All prerequisites satisfied"
}

function Build-DistrolessImages {
    Write-Progress "Building distroless images..."
    
    try {
        $buildScript = Join-Path $PWD "scripts/build-all-distroless-images.ps1"
        
        if (-not (Test-Path $buildScript)) {
            throw "Build script not found: $buildScript"
        }
        
        $buildArgs = @(
            "-ExecutionPolicy", "Bypass"
            "-File", $buildScript
            "-Registry", $Registry
            "-Repository", $Repository
            "-Tag", $Tag
        )
        
        if ($Push) { $buildArgs += "-Push" }
        if ($Force) { $buildArgs += "-Force" }
        if ($Verbose) { $buildArgs += "-Verbose" }
        
        Write-Info "Executing build script with arguments: $($buildArgs -join ' ')"
        
        $buildProcess = Start-Process -FilePath "powershell" -ArgumentList $buildArgs -Wait -PassThru -NoNewWindow
        
        if ($buildProcess.ExitCode -eq 0) {
            Write-Success "Distroless images built successfully"
            $script:DeploymentResults.Build = "Success"
        } else {
            Write-Error "Build failed with exit code: $($buildProcess.ExitCode)"
            $script:DeploymentResults.Build = "Failed"
            throw "Image build failed"
        }
    }
    catch {
        Write-Error "Build process failed: $_"
        $script:DeploymentResults.Build = "Exception"
        throw
    }
}

function Generate-Configurations {
    Write-Progress "Generating service configurations..."
    
    try {
        $configScript = Join-Path $PWD "scripts/generate-service-environments.ps1"
        
        if (-not (Test-Path $configScript)) {
            throw "Configuration script not found: $configScript"
        }
        
        $configArgs = @(
            "-ExecutionPolicy", "Bypass"
            "-File", $configScript
            "-OutputDir", "configs/environment"
        )
        
        if ($Verbose) { $configArgs += "-Verbose" }
        
        Write-Info "Executing configuration script with arguments: $($configArgs -join ' ')"
        
        $configProcess = Start-Process -FilePath "powershell" -ArgumentList $configArgs -Wait -PassThru -NoNewWindow
        
        if ($configProcess.ExitCode -eq 0) {
            Write-Success "Service configurations generated successfully"
            $script:DeploymentResults.Config = "Success"
        } else {
            Write-Error "Configuration generation failed with exit code: $($configProcess.ExitCode)"
            $script:DeploymentResults.Config = "Failed"
            throw "Configuration generation failed"
        }
    }
    catch {
        Write-Error "Configuration generation failed: $_"
        $script:DeploymentResults.Config = "Exception"
        throw
    }
}

function Test-ComposeFile {
    param([string]$ComposeFilePath)
    
    Write-Progress "Validating compose file: $ComposeFilePath"
    
    try {
        if (-not (Test-Path $ComposeFilePath)) {
            throw "Compose file not found: $ComposeFilePath"
        }
        
        # Test compose file syntax
        docker-compose -f $ComposeFilePath config --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "Compose file syntax validation failed"
        }
        
        Write-Success "Compose file validation passed"
        return $true
    }
    catch {
        Write-Error "Compose file validation failed: $_"
        return $false
    }
}

function Deploy-Cluster {
    Write-Progress "Deploying Lucid distroless cluster..."
    
    try {
        $composeFilePath = Join-Path $PWD $ComposeFile
        
        if (-not (Test-ComposeFile $composeFilePath)) {
            throw "Compose file validation failed"
        }
        
        # Load environment variables
        $envFile = Join-Path $PWD "configs/environment/lucid-master.env"
        if (Test-Path $envFile) {
            Write-Info "Loading environment variables from: $envFile"
            Get-Content $envFile | ForEach-Object {
                if ($_ -match "^([^#][^=]+)=(.*)$") {
                    $name = $matches[1].Trim()
                    $value = $matches[2].Trim()
                    [Environment]::SetEnvironmentVariable($name, $value, "Process")
                }
            }
        }
        
        # Stop existing containers
        Write-Info "Stopping existing containers..."
        docker-compose -f $composeFilePath down --remove-orphans
        
        # Pull latest images (if pushing was enabled)
        if ($Push) {
            Write-Info "Pulling latest images..."
            docker-compose -f $composeFilePath pull
        }
        
        # Start the cluster
        Write-Info "Starting Lucid cluster..."
        docker-compose -f $composeFilePath up -d
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Cluster started successfully"
            $script:DeploymentResults.Deploy = "Success"
        } else {
            Write-Error "Cluster startup failed"
            $script:DeploymentResults.Deploy = "Failed"
            throw "Cluster deployment failed"
        }
        
        # Wait for services to be healthy
        Write-Info "Waiting for services to be healthy..."
        Start-Sleep -Seconds 30
        
        # Check service health
        Test-ServiceHealth $composeFilePath
        
    }
    catch {
        Write-Error "Cluster deployment failed: $_"
        $script:DeploymentResults.Deploy = "Exception"
        throw
    }
}

function Test-ServiceHealth {
    param([string]$ComposeFilePath)
    
    Write-Progress "Testing service health..."
    
    try {
        # Get running services
        $services = docker-compose -f $ComposeFilePath ps --services
        $healthyServices = 0
        $totalServices = $services.Count
        
        foreach ($service in $services) {
            Write-Info "Checking health of service: $service"
            
            # Check if container is running
            $containerStatus = docker-compose -f $ComposeFilePath ps $service --format "table {{.State}}"
            if ($containerStatus -match "Up") {
                Write-Success "$service: Running"
                $healthyServices++
            } else {
                Write-Warning "$service: Not running properly"
            }
            
            # Check health endpoint if available
            $healthPort = Get-HealthCheckPort $service
            if ($healthPort) {
                try {
                    $healthResponse = Invoke-WebRequest -Uri "http://localhost:$healthPort/health" -TimeoutSec 5 -UseBasicParsing
                    if ($healthResponse.StatusCode -eq 200) {
                        Write-Success "$service: Health check passed"
                    } else {
                        Write-Warning "$service: Health check failed (HTTP $($healthResponse.StatusCode))"
                    }
                }
                catch {
                    Write-Warning "$service: Health check endpoint not accessible"
                }
            }
        }
        
        Write-Info "Service health summary: $healthyServices/$totalServices services healthy"
        
        if ($healthyServices -eq $totalServices) {
            Write-Success "All services are healthy"
            $script:DeploymentResults.Health = "All Healthy"
        } else {
            Write-Warning "Some services may not be fully healthy"
            $script:DeploymentResults.Health = "Partial"
        }
    }
    catch {
        Write-Error "Health check failed: $_"
        $script:DeploymentResults.Health = "Failed"
    }
}

function Get-HealthCheckPort {
    param([string]$ServiceName)
    
    $portMap = @{
        "admin-ui" = "3000"
        "blockchain-api" = "8084"
        "authentication-service" = "8085"
        "user-manager" = "8086"
        "session-recorder" = "8087"
        "chunker" = "8088"
        "encryptor" = "8089"
        "merkle-builder" = "8090"
        "chain-client" = "8091"
        "tron-client" = "8092"
        "dht-node" = "8093"
        "wallet" = "8094"
        "policy-engine" = "8095"
    }
    
    return $portMap[$ServiceName]
}

function Show-ClusterStatus {
    Write-ColorOutput "`n" + "="*80 "Magenta"
    Write-ColorOutput "LUCID DISTROLESS CLUSTER STATUS" "Magenta"
    Write-ColorOutput "="*80 "Magenta"
    
    # Show deployment results
    Write-Info "Deployment Results:"
    foreach ($result in $script:DeploymentResults.Keys) {
        $status = $script:DeploymentResults[$result]
        $color = switch ($status) {
            "Success" { "Green" }
            "Failed" { "Red" }
            "Exception" { "Red" }
            default { "Yellow" }
        }
        Write-ColorOutput "  $result`: $status" $color
    }
    
    # Show running containers
    Write-Info "`nRunning Containers:"
    try {
        $containers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "label=org.lucid.service"
        Write-ColorOutput $containers "White"
    }
    catch {
        Write-Warning "Could not retrieve container status"
    }
    
    # Show service URLs
    Write-Info "`nService URLs:"
    $serviceUrls = @{
        "Admin UI" = "http://localhost:3000"
        "Blockchain API" = "http://localhost:8084"
        "Authentication Service" = "http://localhost:8085"
        "User Manager" = "http://localhost:8086"
        "Session Recorder" = "http://localhost:8087"
        "Chunker" = "http://localhost:8088"
        "Encryptor" = "http://localhost:8089"
        "Merkle Builder" = "http://localhost:8090"
        "Chain Client" = "http://localhost:8091"
        "TRON Client" = "http://localhost:8092"
        "DHT Node" = "http://localhost:8093"
        "Wallet" = "http://localhost:8094"
        "Policy Engine" = "http://localhost:8095"
    }
    
    foreach ($service in $serviceUrls.Keys) {
        $url = $serviceUrls[$service]
        Write-ColorOutput "  $service`: $url" "Cyan"
    }
    
    # Show deployment time
    $deploymentTime = (Get-Date) - $script:StartTime
    Write-Info "`nTotal deployment time: $($deploymentTime.TotalMinutes.ToString('F2')) minutes"
    
    Write-ColorOutput "`n" + "="*80 "Magenta"
}

function Cleanup-FailedDeployment {
    Write-Progress "Cleaning up failed deployment..."
    
    try {
        $composeFilePath = Join-Path $PWD $ComposeFile
        if (Test-Path $composeFilePath) {
            docker-compose -f $composeFilePath down --remove-orphans --volumes
            Write-Info "Cleaned up containers and volumes"
        }
    }
    catch {
        Write-Warning "Cleanup failed: $_"
    }
}

function Main {
    Write-ColorOutput "LUCID DISTROLESS CLUSTER DEPLOYMENT" "Magenta"
    Write-ColorOutput "Complete deployment of Lucid distroless cluster" "Magenta"
    Write-ColorOutput "Registry: $Registry/$Repository" "Magenta"
    Write-ColorOutput "Environment: $Environment" "Magenta"
    Write-ColorOutput "Push to Registry: $Push" "Magenta"
    Write-ColorOutput ""
    
    try {
        # Test prerequisites
        Test-Prerequisites
        
        # Build distroless images
        if ($Build) {
            Build-DistrolessImages
        }
        
        # Generate configurations
        if ($GenerateConfig) {
            Generate-Configurations
        }
        
        # Deploy cluster
        if ($Deploy) {
            Deploy-Cluster
        }
        
        # Show final status
        Show-ClusterStatus
        
        Write-Success "Lucid distroless cluster deployment completed successfully!"
        
    }
    catch {
        Write-Error "Deployment failed: $_"
        Cleanup-FailedDeployment
        Show-ClusterStatus
        exit 1
    }
}

# Run main function
Main
