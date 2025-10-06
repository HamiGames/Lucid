# LUCID Compliance Validation Script
# Validates all project components against regulations
# Ensures distroless images and YAML composition standards

param(
    [switch]$Verbose = $false,
    [switch]$Fix = $false
)

# Set error handling
$ErrorActionPreference = "Stop"

Write-Host "=== LUCID Compliance Validation ===" -ForegroundColor Green
Write-Host "Validating project against regulations..." -ForegroundColor Yellow
Write-Host ""

$Violations = @()
$Warnings = @()

# Function to log violations
function Add-Violation {
    param(
        [string]$Type,
        [string]$File,
        [string]$Line,
        [string]$Message
    )
    
    $Violations += @{
        Type = $Type
        File = $File
        Line = $Line
        Message = $Message
    }
}

# Function to log warnings
function Add-Warning {
    param(
        [string]$File,
        [string]$Message
    )
    
    $Warnings += @{
        File = $File
        Message = $Message
    }
}

# 1. Check for non-distroless Dockerfiles
Write-Host "1. Checking Dockerfiles for distroless compliance..." -ForegroundColor Cyan

$Dockerfiles = Get-ChildItem -Recurse -Name "Dockerfile*" | Where-Object { $_ -notlike "*simple*" }

foreach ($Dockerfile in $Dockerfiles) {
    $Content = Get-Content $Dockerfile -Raw
    
    # Check for forbidden base images
    $ForbiddenImages = @(
        "FROM python:.*-slim",
        "FROM node:.*-alpine", 
        "FROM ubuntu:",
        "FROM debian:",
        "FROM alpine:",
        "FROM centos:"
    )
    
    foreach ($Pattern in $ForbiddenImages) {
        if ($Content -match $Pattern) {
            Add-Violation -Type "Critical" -File $Dockerfile -Line "" -Message "Non-distroless base image: $($Matches[0])"
        }
    }
    
    # Check for distroless base images
    if ($Content -notmatch "FROM gcr\.io/distroless/") {
        Add-Violation -Type "Critical" -File $Dockerfile -Line "" -Message "No distroless base image found"
    }
    
    # Check for multi-stage build
    if ($Content -notmatch "FROM.*AS.*builder") {
        Add-Warning -File $Dockerfile -Message "No multi-stage build detected"
    }
    
    # Check for non-root user
    if ($Content -notmatch "USER.*nonroot|USER.*[0-9]+") {
        Add-Warning -File $Dockerfile -Message "No non-root user configuration"
    }
}

# 2. Check compose files for build contexts
Write-Host "2. Checking compose files for build contexts..." -ForegroundColor Cyan

$ComposeFiles = Get-ChildItem -Recurse -Name "*.yaml", "*.yml" | Where-Object { $_ -like "*compose*" -or $_ -like "*docker-compose*" }

foreach ($ComposeFile in $ComposeFiles) {
    $Content = Get-Content $ComposeFile -Raw
    
    # Check for build contexts
    if ($Content -match "build:") {
        Add-Violation -Type "Major" -File $ComposeFile -Line "" -Message "Build context found in compose file"
    }
    
    # Check for pull policies
    $Services = [regex]::Matches($Content, "services:\s*\n(.*?)(?=\n\w+:|$)", [System.Text.RegularExpressions.RegexOptions]::Singleline)
    
    foreach ($Service in $Services) {
        if ($Service.Value -notmatch "pull_policy: always") {
            Add-Warning -File $ComposeFile -Message "Missing pull_policy: always in service"
        }
    }
    
    # Check for registry format
    if ($Content -match "image: [^p].*:") {
        Add-Violation -Type "Major" -File $ComposeFile -Line "" -Message "Non-registry image reference found"
    }
}

# 3. Check for proper documentation
Write-Host "3. Checking documentation compliance..." -ForegroundColor Cyan

$Dockerfiles = Get-ChildItem -Recurse -Name "Dockerfile*"

foreach ($Dockerfile in $Dockerfiles) {
    $Content = Get-Content $Dockerfile -Raw
    
    # Check for proper header
    if ($Content -notmatch "# LUCID.*Distroless") {
        Add-Warning -File $Dockerfile -Message "Missing proper documentation header"
    }
    
    # Check for syntax directive
    if ($Content -notmatch "# syntax=docker/dockerfile:1\.7") {
        Add-Warning -File $Dockerfile -Message "Missing Dockerfile syntax directive"
    }
}

# 4. Check network consistency
Write-Host "4. Checking network consistency..." -ForegroundColor Cyan

foreach ($ComposeFile in $ComposeFiles) {
    $Content = Get-Content $ComposeFile -Raw
    
    # Check for lucid_core_net usage
    if ($Content -match "networks:" -and $Content -notmatch "lucid_core_net") {
        Add-Warning -File $ComposeFile -Message "Missing lucid_core_net network definition"
    }
}

# 5. Check volume consistency
Write-Host "5. Checking volume consistency..." -ForegroundColor Cyan

foreach ($ComposeFile in $ComposeFiles) {
    $Content = Get-Content $ComposeFile -Raw
    
    # Check for proper volume naming
    if ($Content -match "volumes:" -and $Content -notmatch "lucid_.*_data") {
        Add-Warning -File $ComposeFile -Message "Non-standard volume naming detected"
    }
}

# Display results
Write-Host ""
Write-Host "=== Compliance Validation Results ===" -ForegroundColor Green

if ($Violations.Count -eq 0) {
    Write-Host "✅ No critical violations found" -ForegroundColor Green
} else {
    Write-Host "❌ Found $($Violations.Count) violations:" -ForegroundColor Red
    
    foreach ($Violation in $Violations) {
        Write-Host "  [$($Violation.Type)] $($Violation.File): $($Violation.Message)" -ForegroundColor Red
    }
}

if ($Warnings.Count -eq 0) {
    Write-Host "✅ No warnings found" -ForegroundColor Green
} else {
    Write-Host "⚠️  Found $($Warnings.Count) warnings:" -ForegroundColor Yellow
    
    foreach ($Warning in $Warnings) {
        Write-Host "  [WARNING] $($Warning.File): $($Warning.Message)" -ForegroundColor Yellow
    }
}

# Summary
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Green
Write-Host "Violations: $($Violations.Count)" -ForegroundColor $(if ($Violations.Count -eq 0) { "Green" } else { "Red" })
Write-Host "Warnings: $($Warnings.Count)" -ForegroundColor $(if ($Warnings.Count -eq 0) { "Green" } else { "Yellow" })

if ($Violations.Count -gt 0) {
    Write-Host ""
    Write-Host "❌ Compliance validation FAILED" -ForegroundColor Red
    Write-Host "Please fix all violations before deployment" -ForegroundColor Red
    exit 1
} else {
    Write-Host ""
    Write-Host "✅ Compliance validation PASSED" -ForegroundColor Green
    Write-Host "Project is compliant with regulations" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Validation Complete ===" -ForegroundColor Green
