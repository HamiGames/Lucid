# Lucid Docker Build Assessment Script - LUCID-STRICT Mode
# Build host: Windows 11 console | Target: Raspberry Pi 5 (ARM64)
# Registry: dockerhub pickme/lucid | Connection: SSH PowerShell terminal
# Follows SPEC-4 clustered build stages and project guidelines

param(
    [switch]$FullClean,
    [switch]$AssessmentOnly,
    [switch]$Build,
    [switch]$Test
)

Write-Host "=== LUCID BUILD ASSESSMENT - LUCID-STRICT MODE ===" -ForegroundColor Cyan
Write-Host "Build Host: Windows 11 | Target: Raspberry Pi 5 (ARM64)" -ForegroundColor Green
Write-Host "Registry: pickme/lucid | SSH Connection Required" -ForegroundColor Green

# === STEP 1: DOCKER ENVIRONMENT ASSESSMENT ===
Write-Host "`n[1] DOCKER ENVIRONMENT STATUS" -ForegroundColor Yellow
Write-Host "Docker Version:" -ForegroundColor White
docker --version

Write-Host "`nDocker System Info:" -ForegroundColor White
docker system df

Write-Host "`nCurrent Containers:" -ForegroundColor White
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

Write-Host "`nCurrent Networks:" -ForegroundColor White
docker network ls --format "table {{.Name}}\t{{.Driver}}\t{{.Scope}}"

Write-Host "`nCurrent Images:" -ForegroundColor White
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# === STEP 2: ARM64 BUILDX SETUP (Pi 5 targeting) ===
Write-Host "`n[2] ARM64 BUILDX MANAGEMENT FOR PI 5" -ForegroundColor Yellow
Write-Host "Current Buildx Builders:" -ForegroundColor White
docker buildx ls

# Check for ARM64 support
$arm64Support = docker buildx ls | Select-String "linux/arm64"
if (-not $arm64Support) {
    Write-Host "⚠ WARNING: No ARM64 builder detected - required for Pi 5" -ForegroundColor Red
}

if ($FullClean) {
    Write-Host "`nCleaning Buildx Cache for ARM64 builds..." -ForegroundColor Red
    docker buildx prune -f
    
    # Remove old builders except essential ones
    Write-Host "Setting up Pi-compatible builder..." -ForegroundColor Red
    $builders = docker buildx ls --format "{{.Name}}" | Where-Object { $_ -ne "default" -and $_ -ne "desktop-linux" }
    foreach ($builder in $builders) {
        if ($builder -and $builder.Trim() -ne "") {
            Write-Host "Removing builder: $builder" -ForegroundColor Red
            try {
                docker buildx rm $builder --force
            } catch {
                Write-Host "Could not remove builder $builder`: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
    }
    
    # Create Pi 5 compatible builder
    Write-Host "Creating ARM64-compatible builder for Pi 5..." -ForegroundColor Green
    docker buildx create --name pi5-builder --platform linux/amd64,linux/arm64 --use --bootstrap
}

# === STEP 3: NETWORK MANAGEMENT ===
Write-Host "`n[3] DOCKER NETWORK MANAGEMENT" -ForegroundColor Yellow

# Clean up old networks if requested
if ($FullClean) {
    Write-Host "Stopping all Lucid containers..." -ForegroundColor Red
    $lucidContainers = docker ps -a --filter "name=lucid" --format "{{.Names}}"
    foreach ($container in $lucidContainers) {
        if ($container -and $container.Trim() -ne "") {
            Write-Host "Stopping container: $container" -ForegroundColor Red
            docker stop $container 2>$null
            docker rm $container 2>$null
        }
    }
    
    Write-Host "Cleaning up Lucid networks..." -ForegroundColor Red
    $lucidNetworks = docker network ls --filter "name=lucid" --format "{{.Name}}"
    foreach ($network in $lucidNetworks) {
        if ($network -and $network.Trim() -ne "" -and $network -ne "bridge" -and $network -ne "host" -and $network -ne "none") {
            Write-Host "Removing network: $network" -ForegroundColor Red
            try {
                docker network rm $network
            } catch {
                Write-Host "Could not remove network $network`: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
    }
}

# Create lucid_net if it doesn't exist
$lucidNetExists = docker network ls --filter "name=lucid-dev_lucid_net" --format "{{.Name}}"
if (-not $lucidNetExists) {
    Write-Host "Creating lucid-dev_lucid_net network..." -ForegroundColor Green
    docker network create lucid-dev_lucid_net --driver bridge --attachable
} else {
    Write-Host "lucid-dev_lucid_net network already exists" -ForegroundColor Green
}

# === STEP 4: PYTHON DEPENDENCIES VERIFICATION ===
Write-Host "`n[4] PYTHON DEPENDENCIES ASSESSMENT" -ForegroundColor Yellow
Write-Host "Checking requirements-dev.txt..." -ForegroundColor White

$requirementsFile = ".devcontainer/requirements-dev.txt"
if (Test-Path $requirementsFile) {
    Write-Host "Requirements file exists" -ForegroundColor Green
    
    # Check for critical missing modules
    $criticalModules = @("httpx", "base58", "blake3", "msgpack", "tronpy", "PyJWT")
    $requirementsContent = Get-Content $requirementsFile -Raw
    
    Write-Host "`nCritical Modules Status:" -ForegroundColor White
    foreach ($module in $criticalModules) {
        if ($requirementsContent -match $module) {
            Write-Host "✓ $module - Found in requirements" -ForegroundColor Green
        } else {
            Write-Host "✗ $module - MISSING from requirements" -ForegroundColor Red
        }
    }
} else {
    Write-Host "Requirements file missing!" -ForegroundColor Red
}

# === STEP 5: __INIT__.PY FILES CHECK ===
Write-Host "`n[5] PYTHON MODULE STRUCTURE ASSESSMENT" -ForegroundColor Yellow
$initFiles = Get-ChildItem -Path . -Name "__init__.py" -Recurse
Write-Host "Found $($initFiles.Count) __init__.py files" -ForegroundColor White

$emptyInitFiles = @()
foreach ($initFile in $initFiles) {
    $content = Get-Content $initFile -Raw -ErrorAction SilentlyContinue
    if (-not $content -or $content.Trim() -eq "") {
        $emptyInitFiles += $initFile
    }
}

if ($emptyInitFiles.Count -gt 0) {
    Write-Host "Found $($emptyInitFiles.Count) empty __init__.py files:" -ForegroundColor Yellow
    foreach ($file in $emptyInitFiles) {
        Write-Host "  - $file" -ForegroundColor Yellow
    }
}

# === STEP 6: DOCKER COMPOSE CONFIGURATION CHECK ===
Write-Host "`n[6] DOCKER COMPOSE CONFIGURATION" -ForegroundColor Yellow
$composeFile = ".devcontainer/docker-compose.dev.yml"
if (Test-Path $composeFile) {
    Write-Host "Docker compose file exists" -ForegroundColor Green
    
    # Check for timestamp issues in image tags
    $composeContent = Get-Content $composeFile -Raw
    if ($composeContent -match ":\d{4}-\d{2}-\d{2}") {
        Write-Host "⚠ WARNING: Found timestamp in image tag (this causes Docker build failures)" -ForegroundColor Red
    } else {
        Write-Host "✓ No timestamp issues found in image tags" -ForegroundColor Green
    }
} else {
    Write-Host "Docker compose file missing!" -ForegroundColor Red
}

# === STEP 7: BUILD EXECUTION ===
if ($Build -and -not $AssessmentOnly) {
    Write-Host "`n[7] EXECUTING BUILD" -ForegroundColor Yellow
    
    # Clean build with proper platform targeting
    Write-Host "Starting clean Docker build..." -ForegroundColor Green
    Write-Host "Building with buildx for linux/amd64..." -ForegroundColor White
    
    $buildStartTime = Get-Date
    
    try {
        # Build for ARM64 (Pi 5 target) using pickme/lucid registry
        Write-Host "Building for ARM64 (Raspberry Pi 5 target)..." -ForegroundColor White
        
        # Use buildx for multi-arch build targeting Pi 5
        docker buildx build --platform linux/arm64 --target final `
            -f .devcontainer/Dockerfile `
            --build-arg BUILDKIT_INLINE_CACHE=1 `
            -t pickme/lucid:dev-arm64 `
            --load .
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Local ARM64 build completed successfully!" -ForegroundColor Green
            $buildEndTime = Get-Date
            $buildDuration = $buildEndTime - $buildStartTime
            Write-Host "Build time: $($buildDuration.TotalMinutes.ToString('F2')) minutes" -ForegroundColor Green
        } else {
            Write-Host "✗ Local ARM64 build failed with exit code $LASTEXITCODE" -ForegroundColor Red
            Write-Host "Attempting SSH remote build on Pi..." -ForegroundColor Yellow
            
            # SSH Remote Build Fallback
            $sshHost = Read-Host "Enter Pi SSH host (e.g., pi@192.168.1.100)"
            if ($sshHost) {
                Write-Host "Initiating SSH remote build on Pi..." -ForegroundColor Cyan
                
                # Create remote build script
                $remoteBuildScript = @"
#!/bin/bash
set -e
echo "=== REMOTE BUILD ON PI 5 ==="
echo "Syncing project files..."

# Navigate to workspace
cd /home/pi/Lucid 2>/dev/null || {
    echo "Creating workspace directory..."
    mkdir -p /home/pi/Lucid
    cd /home/pi/Lucid
}

# Build on Pi natively
echo "Building natively on Pi 5 (ARM64)..."
docker build -f .devcontainer/Dockerfile --target final -t pickme/lucid:dev-arm64 .

if [ `$? -eq 0 ]; then
    echo "✓ Pi native build completed successfully!"
    docker images | grep pickme/lucid
else
    echo "✗ Pi native build failed!"
    exit 1
fi
"@
                
                # Write script to temp file
                $tempScript = [System.IO.Path]::GetTempFileName() + ".sh"
                $remoteBuildScript | Out-File -FilePath $tempScript -Encoding UTF8
                
                # Copy project files to Pi
                Write-Host "Copying project files to Pi..." -ForegroundColor White
                scp -r . "$sshHost":/home/pi/Lucid/
                
                # Copy and execute build script
                Write-Host "Executing remote build on Pi..." -ForegroundColor White
                scp $tempScript "$sshHost":/tmp/remote-build.sh
                ssh $sshHost "chmod +x /tmp/remote-build.sh && /tmp/remote-build.sh"
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "✓ SSH remote build completed successfully!" -ForegroundColor Green
                } else {
                    Write-Host "✗ SSH remote build failed!" -ForegroundColor Red
                }
                
                # Cleanup temp file
                Remove-Item $tempScript -Force
            } else {
                Write-Host "No SSH host provided - build failed" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "✗ Build error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Consider using SSH remote build option" -ForegroundColor Yellow
    }
}

# === STEP 8: TESTING ===
if ($Test -and -not $AssessmentOnly) {
    Write-Host "`n[8] RUNNING TESTS" -ForegroundColor Yellow
    
    # Start the services
    Write-Host "Starting services..." -ForegroundColor Green
    docker-compose -f .devcontainer/docker-compose.dev.yml up -d
    
    # Wait for services to be ready
    Write-Host "Waiting for services to start..." -ForegroundColor White
    Start-Sleep -Seconds 30
    
    # Check service health
    Write-Host "`nService Status:" -ForegroundColor White
    docker-compose -f .devcontainer/docker-compose.dev.yml ps
    
    # Test API endpoints
    Write-Host "`nTesting API endpoints..." -ForegroundColor White
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method GET -TimeoutSec 10
        Write-Host "✓ API Gateway health check passed" -ForegroundColor Green
    } catch {
        Write-Host "✗ API Gateway health check failed: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    # Test MongoDB connection
    Write-Host "Testing MongoDB connection..." -ForegroundColor White
    try {
        docker exec lucid_mongo mongosh --quiet -u lucid -p lucid --authenticationDatabase admin --eval "db.runCommand({ping: 1})"
        Write-Host "✓ MongoDB connection successful" -ForegroundColor Green
    } catch {
        Write-Host "✗ MongoDB connection failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# === FINAL RECOMMENDATIONS ===
Write-Host "`n=== BUILD ASSESSMENT COMPLETE ===" -ForegroundColor Cyan
Write-Host "`nRECOMMENDATIONS:" -ForegroundColor Yellow

if ($emptyInitFiles.Count -gt 0) {
    Write-Host "• Fix empty __init__.py files to enable proper Python imports" -ForegroundColor White
}

$requirementsContent = if (Test-Path $requirementsFile) { Get-Content $requirementsFile -Raw } else { "" }
$criticalModules = @("httpx", "base58", "blake3", "msgpack", "tronpy", "PyJWT")
$missingModules = $criticalModules | Where-Object { $requirementsContent -notmatch $_ }

if ($missingModules.Count -gt 0) {
    Write-Host "• Add missing critical modules to requirements: $($missingModules -join ', ')" -ForegroundColor White
}

Write-Host "• Use 'build-assessment.ps1 -FullClean -Build -Test' for complete rebuild" -ForegroundColor White
Write-Host "• Use 'setup-dev-container.sh' for complete environment setup" -ForegroundColor White

Write-Host "`nNext Steps:" -ForegroundColor Green
Write-Host "1. Run with -FullClean to clean environment" -ForegroundColor White
Write-Host "2. Run with -Build to build containers" -ForegroundColor White
Write-Host "3. Run with -Test to validate setup" -ForegroundColor White
Write-Host "4. Run setup-dev-container.sh for complete setup" -ForegroundColor White