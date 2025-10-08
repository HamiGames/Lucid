# LUCID DISTROLESS IMAGE BUILDER
# Professional distroless image building script for Lucid project
# Builds all Dockerfiles in infrastructure/docker/ as distroless images
# Multi-platform build for ARM64 Pi and AMD64 development

param(
    [switch]$Push = $false,
    [switch]$Force = $false,
    [switch]$Verbose = $false,
    [string]$Registry = "pickme",
    [string]$Repository = "lucid",
    [string]$Tag = "latest",
    [string]$DockerDir = "infrastructure/docker",
    [string]$ComposeDir = "infrastructure/compose"
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
$script:BuildResults = @{}
$script:ComposeServices = @{}
$script:TotalImages = 0
$script:BuiltImages = 0
$script:FailedImages = 0

# Docker buildx configuration
$DOCKER_BUILDX_PLATFORMS = "linux/amd64,linux/arm64"
$DOCKER_BUILDX_BUILDER = "lucid-multiplatform"

# Service configuration templates
$ServiceConfigs = @{
    "admin-ui" = @{
        Port = 3000
        Environment = @{
            "NODE_ENV" = "production"
            "NEXT_TELEMETRY_DISABLED" = "1"
            "PORT" = "3000"
            "HOSTNAME" = "0.0.0.0"
            "NEXT_PUBLIC_API_URL" = "http://localhost:8081"
            "NEXT_PUBLIC_WS_URL" = "ws://localhost:8081/ws"
        }
        HealthCheck = @{
            Test = @("CMD", "curl", "-f", "http://localhost:3000/health")
            Interval = "30s"
            Timeout = "10s"
            Retries = 3
        }
    }
    "blockchain-api" = @{
        Port = 8084
        Environment = @{
            "PYTHONDONTWRITEBYTECODE" = "1"
            "PYTHONUNBUFFERED" = "1"
            "API_HOST" = "0.0.0.0"
            "API_PORT" = "8084"
            "UVICORN_WORKERS" = "1"
            "MONGO_URI" = "mongodb://lucid:lucid@mongodb:27017/lucid"
            "TRON_NETWORK" = "shasta"
        }
        HealthCheck = @{
            Test = @("CMD", "curl", "-f", "http://localhost:8084/health")
            Interval = "30s"
            Timeout = "10s"
            Retries = 3
        }
    }
    "authentication-service" = @{
        Port = 8085
        Environment = @{
            "PYTHONDONTWRITEBYTECODE" = "1"
            "PYTHONUNBUFFERED" = "1"
            "API_HOST" = "0.0.0.0"
            "API_PORT" = "8085"
            "MONGO_URI" = "mongodb://lucid:lucid@mongodb:27017/lucid"
            "JWT_SECRET_KEY" = "lucid-jwt-secret-key-change-in-production"
        }
        HealthCheck = @{
            Test = @("CMD", "curl", "-f", "http://localhost:8085/health")
            Interval = "30s"
            Timeout = "10s"
            Retries = 3
        }
    }
    "mongodb" = @{
        Port = 27017
        Environment = @{
            "MONGO_INITDB_ROOT_USERNAME" = "lucid"
            "MONGO_INITDB_ROOT_PASSWORD" = "lucid"
            "MONGO_INITDB_DATABASE" = "lucid"
        }
        HealthCheck = @{
            Test = @("CMD", "mongosh", "--eval", "db.adminCommand('ping')")
            Interval = "30s"
            Timeout = "10s"
            Retries = 3
        }
    }
}

function Initialize-DockerBuildx {
    Write-Progress "Initializing Docker Buildx for multi-platform builds..."
    
    try {
        # Check if Docker is running
        docker version | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker is not running or not accessible"
        }
        
        # Create buildx builder if it doesn't exist
        $builderExists = docker buildx ls | Select-String $DOCKER_BUILDX_BUILDER
        if (-not $builderExists) {
            Write-Info "Creating buildx builder: $DOCKER_BUILDX_BUILDER"
            docker buildx create --name $DOCKER_BUILDX_BUILDER --use
        } else {
            Write-Info "Using existing buildx builder: $DOCKER_BUILDX_BUILDER"
            docker buildx use $DOCKER_BUILDX_BUILDER
        }
        
        # Bootstrap the builder
        docker buildx inspect --bootstrap
        Write-Success "Docker Buildx initialized successfully"
    }
    catch {
        Write-Error "Failed to initialize Docker Buildx: $_"
        throw
    }
}

function Get-Dockerfiles {
    Write-Progress "Scanning for Dockerfiles in $DockerDir..."
    
    $dockerfiles = @()
    $dockerDirPath = Join-Path $PWD $DockerDir
    
    if (-not (Test-Path $dockerDirPath)) {
        throw "Docker directory not found: $dockerDirPath"
    }
    
    # Find all Dockerfiles, prioritizing distroless versions
    Get-ChildItem -Path $dockerDirPath -Recurse -Name "Dockerfile*" | ForEach-Object {
        $dockerfilePath = Join-Path $dockerDirPath $_
        $relativePath = $_.Replace("$DockerDir/", "").Replace("\", "/")
        
        # Skip non-distroless files if distroless version exists
        $isDistroless = $_.Contains(".distroless")
        $baseName = $_.Replace(".distroless", "").Replace("Dockerfile.", "")
        
        if ($isDistroless -or -not (Get-ChildItem -Path (Split-Path $dockerfilePath) -Name "*distroless*" -ErrorAction SilentlyContinue)) {
            $dockerfiles += @{
                Path = $dockerfilePath
                RelativePath = $relativePath
                Directory = Split-Path $relativePath
                Name = Split-Path $relativePath -Leaf
                ServiceName = $baseName
                IsDistroless = $isDistroless
            }
        }
    }
    
    Write-Info "Found $($dockerfiles.Count) Dockerfiles to build"
    $script:TotalImages = $dockerfiles.Count
    
    return $dockerfiles
}

function Test-Dockerfile {
    param([hashtable]$DockerfileInfo)
    
    Write-Info "Validating Dockerfile: $($DockerfileInfo.RelativePath)"
    
    try {
        # Check if Dockerfile exists and is readable
        if (-not (Test-Path $DockerfileInfo.Path)) {
            throw "Dockerfile not found: $($DockerfileInfo.Path)"
        }
        
        # Read Dockerfile content
        $content = Get-Content $DockerfileInfo.Path -Raw
        
        # Validate distroless compliance
        if ($DockerfileInfo.IsDistroless) {
            if ($content -notmatch "FROM gcr\.io/distroless/") {
                Write-Warning "Dockerfile may not be distroless compliant: $($DockerfileInfo.RelativePath)"
            }
        }
        
        # Check for required labels
        if ($content -notmatch "LABEL.*org\.lucid\.service") {
            Write-Warning "Missing org.lucid.service label in: $($DockerfileInfo.RelativePath)"
        }
        
        # Check for multi-stage build
        if ($content -notmatch "FROM.*AS.*builder") {
            Write-Warning "Not a multi-stage build: $($DockerfileInfo.RelativePath)"
        }
        
        # Validate syntax directive
        if ($content -notmatch "# syntax=docker/dockerfile:1\.[0-9]+") {
            Write-Warning "Missing syntax directive in: $($DockerfileInfo.RelativePath)"
        }
        
        Write-Success "Dockerfile validation passed: $($DockerfileInfo.RelativePath)"
        return $true
    }
    catch {
        Write-Error "Dockerfile validation failed: $_"
        return $false
    }
}

function Build-DockerImage {
    param([hashtable]$DockerfileInfo)
    
    $serviceName = $DockerfileInfo.ServiceName
    $imageName = "${Registry}/${Repository}:${serviceName}"
    $dockerfilePath = $DockerfileInfo.Path
    $contextPath = Split-Path $dockerfilePath
    
    Write-Progress "Building image: $imageName"
    Write-Info "  Dockerfile: $($DockerfileInfo.RelativePath)"
    Write-Info "  Context: $contextPath"
    
    try {
        # Build command
        $buildArgs = @(
            "buildx", "build"
            "--platform", $DOCKER_BUILDX_PLATFORMS
            "--file", $dockerfilePath
            "--tag", $imageName
            "--label", "org.lucid.built-by=lucid-distroless-builder"
            "--label", "org.lucid.built-at=$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')"
            "--label", "org.lucid.git-commit=$(git rev-parse HEAD 2>$null || echo 'unknown')"
        )
        
        if ($Push) {
            $buildArgs += "--push"
        } else {
            $buildArgs += "--load"
        }
        
        if ($Force) {
            $buildArgs += "--no-cache"
        }
        
        $buildArgs += $contextPath
        
        # Execute build
        if ($Verbose) {
            Write-Info "Build command: docker $($buildArgs -join ' ')"
        }
        
        $buildOutput = docker @buildArgs 2>&1
        $buildExitCode = $LASTEXITCODE
        
        if ($buildExitCode -eq 0) {
            Write-Success "Successfully built: $imageName"
            $script:BuiltImages++
            $script:BuildResults[$serviceName] = @{
                Status = "Success"
                ImageName = $imageName
                BuildTime = Get-Date
            }
            return $true
        } else {
            Write-Error "Build failed for: $imageName"
            Write-Error "Build output: $buildOutput"
            $script:FailedImages++
            $script:BuildResults[$serviceName] = @{
                Status = "Failed"
                ImageName = $imageName
                Error = $buildOutput
                BuildTime = Get-Date
            }
            return $false
        }
    }
    catch {
        Write-Error "Build exception for $serviceName : $_"
        $script:FailedImages++
        $script:BuildResults[$serviceName] = @{
            Status = "Exception"
            ImageName = $imageName
            Error = $_.ToString()
            BuildTime = Get-Date
        }
        return $false
    }
}

function Generate-ComposeService {
    param([hashtable]$DockerfileInfo)
    
    $serviceName = $DockerfileInfo.ServiceName
    $imageName = "${Registry}/${Repository}:${serviceName}"
    
    # Get service configuration
    $config = $ServiceConfigs[$serviceName]
    if (-not $config) {
        # Default configuration
        $config = @{
            Port = 8080
            Environment = @{}
            HealthCheck = $null
        }
    }
    
    # Generate service definition
    $serviceDef = @{
        image = $imageName
        pull_policy = "always"
        networks = @("lucid_core_net")
        restart = "unless-stopped"
    }
    
    # Add port mapping
    if ($config.Port) {
        $serviceDef.ports = @("$($config.Port):$($config.Port)")
    }
    
    # Add environment variables
    if ($config.Environment.Count -gt 0) {
        $serviceDef.environment = $config.Environment
    }
    
    # Add health check
    if ($config.HealthCheck) {
        $serviceDef.healthcheck = $config.HealthCheck
    }
    
    # Add volumes for data persistence
    $volumeName = "lucid_${serviceName}_data"
    $serviceDef.volumes = @("${volumeName}:/data")
    
    $script:ComposeServices[$serviceName] = $serviceDef
}

function Generate-ComposeFile {
    param([string]$OutputPath)
    
    Write-Progress "Generating Docker Compose file: $OutputPath"
    
    $composeContent = @"
# LUCID DISTROLESS DEPLOYMENT - Generated by build-all-distroless-images.ps1
# Complete distroless deployment with all built images
# Multi-platform deployment for ARM64 Pi and AMD64 development

version: '3.8'

networks:
  lucid_core_net:
    name: lucid_core_net
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/24
          gateway: 172.21.0.1

volumes:
"@
    
    # Add volumes for each service
    foreach ($serviceName in $script:ComposeServices.Keys) {
        $volumeName = "lucid_${serviceName}_data"
        $composeContent += @"

  ${volumeName}:
    name: ${volumeName}
    labels:
      - "org.lucid.layer=1"
      - "org.lucid.volume=${serviceName}"
"@
    }
    
    $composeContent += @"

services:
"@
    
    # Add services
    foreach ($serviceName in $script:ComposeServices.Keys | Sort-Object) {
        $service = $script:ComposeServices[$serviceName]
        
        $composeContent += @"

  ${serviceName}:
    image: $($service.image)
    pull_policy: $($service.pull_policy)
    networks:
      - lucid_core_net
    restart: $($service.restart)
"@
        
        if ($service.ports) {
            foreach ($port in $service.ports) {
                $composeContent += "`n    ports:`n      - `"$port`""
            }
        }
        
        if ($service.environment) {
            $composeContent += "`n    environment:"
            foreach ($envKey in $service.environment.Keys | Sort-Object) {
                $envValue = $service.environment[$envKey]
                $composeContent += "`n      - `"$envKey=$envValue`""
            }
        }
        
        if ($service.volumes) {
            $composeContent += "`n    volumes:"
            foreach ($volume in $service.volumes) {
                $composeContent += "`n      - $volume"
            }
        }
        
        if ($service.healthcheck) {
            $composeContent += "`n    healthcheck:"
            $composeContent += "`n      test: $($service.healthcheck.Test -join ' ')"
            $composeContent += "`n      interval: $($service.healthcheck.Interval)"
            $composeContent += "`n      timeout: $($service.healthcheck.Timeout)"
            $composeContent += "`n      retries: $($service.healthcheck.Retries)"
        }
        
        $composeContent += "`n"
    }
    
    # Write compose file
    try {
        $outputDir = Split-Path $OutputPath
        if (-not (Test-Path $outputDir)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }
        
        $composeContent | Out-File -FilePath $OutputPath -Encoding UTF8
        Write-Success "Generated compose file: $OutputPath"
    }
    catch {
        Write-Error "Failed to generate compose file: $_"
        throw
    }
}

function Show-BuildSummary {
    Write-ColorOutput "`n" + "="*80 "Magenta"
    Write-ColorOutput "LUCID DISTROLESS BUILD SUMMARY" "Magenta"
    Write-ColorOutput "="*80 "Magenta"
    
    Write-Info "Total Images: $script:TotalImages"
    Write-Success "Built Successfully: $script:BuiltImages"
    Write-Error "Failed: $script:FailedImages"
    
    if ($script:FailedImages -gt 0) {
        Write-Warning "`nFailed Images:"
        foreach ($serviceName in $script:BuildResults.Keys) {
            $result = $script:BuildResults[$serviceName]
            if ($result.Status -ne "Success") {
                Write-Error "  - $serviceName ($($result.Status))"
                if ($result.Error) {
                    Write-Error "    Error: $($result.Error)"
                }
            }
        }
    }
    
    Write-Info "`nSuccessfully Built Images:"
    foreach ($serviceName in $script:BuildResults.Keys) {
        $result = $script:BuildResults[$serviceName]
        if ($result.Status -eq "Success") {
            Write-Success "  - $($result.ImageName)"
        }
    }
    
    Write-ColorOutput "`n" + "="*80 "Magenta"
}

# Main execution
function Main {
    Write-ColorOutput "LUCID DISTROLESS IMAGE BUILDER" "Magenta"
    Write-ColorOutput "Building all Dockerfiles as distroless images" "Magenta"
    Write-ColorOutput "Registry: $Registry/$Repository" "Magenta"
    Write-ColorOutput "Push to Registry: $Push" "Magenta"
    Write-ColorOutput ""
    
    try {
        # Initialize Docker Buildx
        Initialize-DockerBuildx
        
        # Get all Dockerfiles
        $dockerfiles = Get-Dockerfiles
        
        # Build each image
        foreach ($dockerfile in $dockerfiles) {
            Write-ColorOutput "`n" + "-"*60 "Yellow"
            
            # Validate Dockerfile
            if (-not (Test-Dockerfile $dockerfile)) {
                Write-Warning "Skipping invalid Dockerfile: $($dockerfile.RelativePath)"
                continue
            }
            
            # Build image
            if (Build-DockerImage $dockerfile) {
                # Generate compose service
                Generate-ComposeService $dockerfile
            }
        }
        
        # Generate compose file
        if ($script:ComposeServices.Count -gt 0) {
            $composePath = Join-Path $ComposeDir "lucid-distroless-complete.yaml"
            Generate-ComposeFile $composePath
        }
        
        # Show summary
        Show-BuildSummary
        
        if ($script:FailedImages -eq 0) {
            Write-Success "All images built successfully!"
            exit 0
        } else {
            Write-Warning "Some images failed to build. Check the summary above."
            exit 1
        }
    }
    catch {
        Write-Error "Build process failed: $_"
        Show-BuildSummary
        exit 1
    }
}

# Run main function
Main
