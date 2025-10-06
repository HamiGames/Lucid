# LUCID Layer 2 Dockerfile Verification Script
# Verifies all Layer 2 Dockerfiles are correctly composed before building

param(
    [switch]$Verbose = $false
)

Write-Host "=== LUCID Layer 2 Dockerfile Verification ===" -ForegroundColor Green
Write-Host ""

$Dockerfiles = @(
    @{
        Path = "RDP/server/Dockerfile.server-manager"
        Name = "RDP Server Manager"
        ExpectedBase = "gcr.io/distroless/python3-debian12:nonroot"
    },
    @{
        Path = "RDP/server/Dockerfile.xrdp-integration"
        Name = "xrdp Integration"
        ExpectedBase = "gcr.io/distroless/base-debian12:nonroot"
    },
    @{
        Path = "blockchain/deployment/Dockerfile.contract-deployment"
        Name = "Contract Deployment"
        ExpectedBase = "gcr.io/distroless/python3-debian12:nonroot"
    }
)

$AllValid = $true

foreach ($Dockerfile in $Dockerfiles) {
    Write-Host "Verifying $($Dockerfile.Name)..." -ForegroundColor Cyan
    
    if (-not (Test-Path $Dockerfile.Path)) {
        Write-Host "❌ Dockerfile not found: $($Dockerfile.Path)" -ForegroundColor Red
        $AllValid = $false
        continue
    }
    
    # Check if file is not empty
    $Content = Get-Content $Dockerfile.Path -Raw
    if ([string]::IsNullOrWhiteSpace($Content)) {
        Write-Host "❌ Dockerfile is empty: $($Dockerfile.Path)" -ForegroundColor Red
        $AllValid = $false
        continue
    }
    
    # Check for distroless base image
    if ($Content -match "FROM\s+$($Dockerfile.ExpectedBase)") {
        Write-Host "✅ Distroless base image correct: $($Dockerfile.ExpectedBase)" -ForegroundColor Green
    } else {
        Write-Host "❌ Distroless base image incorrect or missing" -ForegroundColor Red
        Write-Host "   Expected: $($Dockerfile.ExpectedBase)" -ForegroundColor Yellow
        $AllValid = $false
    }
    
    # Check for multi-stage build
    if ($Content -match "FROM.*AS.*builder") {
        Write-Host "✅ Multi-stage build detected" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Multi-stage build not detected" -ForegroundColor Yellow
    }
    
    # Check for syntax directive
    if ($Content -match "# syntax=docker/dockerfile:1\.7") {
        Write-Host "✅ Dockerfile syntax directive present" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Dockerfile syntax directive missing" -ForegroundColor Yellow
    }
    
    # Check for metadata labels
    if ($Content -match "LABEL.*maintainer") {
        Write-Host "✅ Metadata labels present" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Metadata labels missing" -ForegroundColor Yellow
    }
    
    # Check for non-root user
    if ($Content -match "USER.*[a-zA-Z]") {
        Write-Host "✅ Non-root user configured" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Non-root user not configured" -ForegroundColor Yellow
    }
    
    if ($Verbose) {
        Write-Host "Dockerfile content preview:" -ForegroundColor Gray
        Get-Content $Dockerfile.Path | Select-Object -First 10 | ForEach-Object {
            Write-Host "  $_" -ForegroundColor Gray
        }
    }
    
    Write-Host ""
}

if ($AllValid) {
    Write-Host "=== All Dockerfiles are valid ===" -ForegroundColor Green
    Write-Host "Ready to build Layer 2 distroless images" -ForegroundColor Green
    exit 0
} else {
    Write-Host "=== Some Dockerfiles have issues ===" -ForegroundColor Red
    Write-Host "Please fix the issues before building" -ForegroundColor Red
    exit 1
}
