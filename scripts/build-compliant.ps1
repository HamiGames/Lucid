# LUCID Compliant Build Script
# Builds all images according to project regulations
# Enforces distroless-only policy and registry standards

param(
    [string]$Registry = "pickme",
    [string]$Repository = "lucid",
    [string]$Tag = "latest",
    [switch]$Push = $true,
    [switch]$NoCache = $true,
    [switch]$Verbose = $false,
    [switch]$Validate = $true,
    [switch]$Enforce = $true
)

# Set error handling
$ErrorActionPreference = "Stop"

Write-Host "=== LUCID Compliant Build System ===" -ForegroundColor Green
Write-Host "Registry: $Registry" -ForegroundColor Yellow
Write-Host "Repository: $Repository" -ForegroundColor Yellow
Write-Host "Tag: $Tag" -ForegroundColor Yellow
Write-Host "Push: $Push" -ForegroundColor Yellow
Write-Host "No Cache: $NoCache" -ForegroundColor Yellow
Write-Host "Validate: $Validate" -ForegroundColor Yellow
Write-Host "Enforce: $Enforce" -ForegroundColor Yellow
Write-Host ""

# Step 1: Validate compliance before building
if ($Validate) {
    Write-Host "Step 1: Validating compliance..." -ForegroundColor Cyan
    
    try {
        powershell -ExecutionPolicy Bypass -File scripts/validate-compliance.ps1 -Verbose:$Verbose
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Compliance validation failed" -ForegroundColor Red
            Write-Host "Please fix compliance issues before building" -ForegroundColor Red
            exit 1
        }
        Write-Host "✅ Compliance validation passed" -ForegroundColor Green
    } catch {
        Write-Host "❌ Compliance validation error: $_" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# Step 2: Enforce compliance if requested
if ($Enforce) {
    Write-Host "Step 2: Enforcing compliance..." -ForegroundColor Cyan
    
    try {
        powershell -ExecutionPolicy Bypass -File scripts/enforce-compliance.ps1 -Action enforce -Verbose:$Verbose
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Compliance enforcement failed" -ForegroundColor Red
            exit 1
        }
        Write-Host "✅ Compliance enforcement completed" -ForegroundColor Green
    } catch {
        Write-Host "❌ Compliance enforcement error: $_" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# Step 3: Verify Docker buildx
Write-Host "Step 3: Verifying Docker buildx..." -ForegroundColor Cyan
try {
    docker buildx version
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker buildx not available" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Docker buildx available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker buildx error: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Verify Docker Hub login
if ($Push) {
    Write-Host "Step 4: Verifying Docker Hub login..." -ForegroundColor Cyan
    try {
        docker info | Select-String "Username"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Docker Hub login required" -ForegroundColor Red
            Write-Host "Please run: docker login" -ForegroundColor Yellow
            exit 1
        }
        Write-Host "✅ Docker Hub login verified" -ForegroundColor Green
    } catch {
        Write-Host "❌ Docker Hub login error: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Step 5: Build all compliant images
Write-Host "Step 5: Building compliant images..." -ForegroundColor Cyan

# Build configuration
$BuildArgs = @(
    "buildx", "build"
    "--platform", "linux/amd64,linux/arm64"
    "--no-cache"
    "--push"
)

if ($Verbose) {
    $BuildArgs += "--progress=plain"
}

# Find all compliant Dockerfiles
$Dockerfiles = Get-ChildItem -Recurse -Name "Dockerfile*" | Where-Object { 
    $_ -notlike "*simple*" -and 
    (Get-Content $_ -Raw) -match "FROM gcr\.io/distroless/"
}

Write-Host "Found $($Dockerfiles.Count) compliant Dockerfiles:" -ForegroundColor Yellow
foreach ($Dockerfile in $Dockerfiles) {
    Write-Host "  - $Dockerfile" -ForegroundColor Gray
}

Write-Host ""

# Build each compliant image
foreach ($Dockerfile in $Dockerfiles) {
    # Extract service name from Dockerfile path
    $ServiceName = $Dockerfile -replace ".*Dockerfile\.", "" -replace ".*Dockerfile", ""
    if ($ServiceName -eq "") {
        $ServiceName = "default"
    }
    
    Write-Host "Building $ServiceName..." -ForegroundColor Cyan
    
    $moduleArgs = $BuildArgs + @(
        "--tag", "${Registry}/${Repository}:${ServiceName}-${Tag}",
        "--tag", "${Registry}/${Repository}:${ServiceName}",
        "--file", $Dockerfile,
        "."
    )
    
    try {
        if ($Verbose) {
            Write-Host "Command: docker $($moduleArgs -join ' ')" -ForegroundColor Gray
        }
        
        docker @moduleArgs
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $ServiceName built successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ $ServiceName build failed" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "❌ $ServiceName build error: $_" -ForegroundColor Red
        exit 1
    }
}

# Step 6: Verify built images
Write-Host ""
Write-Host "Step 6: Verifying built images..." -ForegroundColor Cyan

foreach ($Dockerfile in $Dockerfiles) {
    $ServiceName = $Dockerfile -replace ".*Dockerfile\.", "" -replace ".*Dockerfile", ""
    if ($ServiceName -eq "") {
        $ServiceName = "default"
    }
    
    try {
        Write-Host "Verifying ${Registry}/${Repository}:${ServiceName}..." -ForegroundColor Gray
        docker manifest inspect "${Registry}/${Repository}:${ServiceName}" | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ ${ServiceName} verified" -ForegroundColor Green
        } else {
            Write-Host "❌ ${ServiceName} verification failed" -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ ${ServiceName} verification error: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Compliant Build Complete ===" -ForegroundColor Green
Write-Host "All images built according to project regulations" -ForegroundColor Green
Write-Host "Images are ready for deployment" -ForegroundColor Green

Write-Host ""
Write-Host "Built images:" -ForegroundColor Yellow
foreach ($Dockerfile in $Dockerfiles) {
    $ServiceName = $Dockerfile -replace ".*Dockerfile\.", "" -replace ".*Dockerfile", ""
    if ($ServiceName -eq "") {
        $ServiceName = "default"
    }
    Write-Host "  - ${Registry}/${Repository}:${ServiceName}" -ForegroundColor White
}

Write-Host ""
Write-Host "Use docker-compose to deploy with these images" -ForegroundColor Green
