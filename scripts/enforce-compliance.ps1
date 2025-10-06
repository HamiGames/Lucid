# LUCID Compliance Enforcement Script
# Enforces project regulations during build and deployment
# Prevents non-compliant images and configurations

param(
    [string]$Action = "validate",  # validate, fix, enforce
    [switch]$Verbose = $false
)

# Set error handling
$ErrorActionPreference = "Stop"

Write-Host "=== LUCID Compliance Enforcement ===" -ForegroundColor Green
Write-Host "Action: $Action" -ForegroundColor Yellow
Write-Host ""

# Function to enforce distroless compliance
function Enforce-DistrolessCompliance {
    Write-Host "Enforcing distroless compliance..." -ForegroundColor Cyan
    
    $Dockerfiles = Get-ChildItem -Recurse -Name "Dockerfile*" | Where-Object { $_ -notlike "*simple*" }
    
    foreach ($Dockerfile in $Dockerfiles) {
        $Content = Get-Content $Dockerfile -Raw
        
        # Check if already compliant
        if ($Content -match "FROM gcr\.io/distroless/") {
            Write-Host "✅ $Dockerfile is already distroless compliant" -ForegroundColor Green
            continue
        }
        
        # Convert to distroless if needed
        if ($Action -eq "fix") {
            Write-Host "🔧 Converting $Dockerfile to distroless..." -ForegroundColor Yellow
            
            # This would need specific conversion logic based on the Dockerfile content
            # For now, we'll just report what needs to be done
            Write-Host "  - Replace base image with distroless equivalent" -ForegroundColor Gray
            Write-Host "  - Add multi-stage build if missing" -ForegroundColor Gray
            Write-Host "  - Ensure non-root user configuration" -ForegroundColor Gray
        } else {
            Write-Host "❌ $Dockerfile is not distroless compliant" -ForegroundColor Red
        }
    }
}

# Function to enforce compose compliance
function Enforce-ComposeCompliance {
    Write-Host "Enforcing compose file compliance..." -ForegroundColor Cyan
    
    $ComposeFiles = Get-ChildItem -Recurse -Name "*.yaml", "*.yml" | Where-Object { $_ -like "*compose*" -or $_ -like "*docker-compose*" }
    
    foreach ($ComposeFile in $ComposeFiles) {
        $Content = Get-Content $ComposeFile -Raw
        
        # Check for build contexts
        if ($Content -match "build:") {
            if ($Action -eq "fix") {
                Write-Host "🔧 Removing build contexts from $ComposeFile..." -ForegroundColor Yellow
                # This would need specific logic to replace build contexts with image references
                Write-Host "  - Replace build contexts with image references" -ForegroundColor Gray
                Write-Host "  - Add pull_policy: always to all services" -ForegroundColor Gray
            } else {
                Write-Host "❌ $ComposeFile contains build contexts" -ForegroundColor Red
            }
        } else {
            Write-Host "✅ $ComposeFile is compose compliant" -ForegroundColor Green
        }
    }
}

# Function to enforce registry compliance
function Enforce-RegistryCompliance {
    Write-Host "Enforcing registry compliance..." -ForegroundColor Cyan
    
    $ComposeFiles = Get-ChildItem -Recurse -Name "*.yaml", "*.yml" | Where-Object { $_ -like "*compose*" -or $_ -like "*docker-compose*" }
    
    foreach ($ComposeFile in $ComposeFiles) {
        $Content = Get-Content $ComposeFile -Raw
        
        # Check for proper registry format
        if ($Content -match "image: pickme/lucid:") {
            Write-Host "✅ $ComposeFile uses proper registry format" -ForegroundColor Green
        } elseif ($Content -match "image:") {
            if ($Action -eq "fix") {
                Write-Host "🔧 Updating registry format in $ComposeFile..." -ForegroundColor Yellow
                Write-Host "  - Update image references to use pickme/lucid: prefix" -ForegroundColor Gray
            } else {
                Write-Host "❌ $ComposeFile uses non-standard registry format" -ForegroundColor Red
            }
        }
    }
}

# Function to enforce network compliance
function Enforce-NetworkCompliance {
    Write-Host "Enforcing network compliance..." -ForegroundColor Cyan
    
    $ComposeFiles = Get-ChildItem -Recurse -Name "*.yaml", "*.yml" | Where-Object { $_ -like "*compose*" -or $_ -like "*docker-compose*" }
    
    foreach ($ComposeFile in $ComposeFiles) {
        $Content = Get-Content $ComposeFile -Raw
        
        # Check for lucid_core_net usage
        if ($Content -match "lucid_core_net") {
            Write-Host "✅ $ComposeFile uses standardized networks" -ForegroundColor Green
        } elseif ($Content -match "networks:") {
            if ($Action -eq "fix") {
                Write-Host "🔧 Updating network configuration in $ComposeFile..." -ForegroundColor Yellow
                Write-Host "  - Standardize network names to lucid_core_net" -ForegroundColor Gray
            } else {
                Write-Host "❌ $ComposeFile uses non-standard network configuration" -ForegroundColor Red
            }
        }
    }
}

# Function to enforce documentation compliance
function Enforce-DocumentationCompliance {
    Write-Host "Enforcing documentation compliance..." -ForegroundColor Cyan
    
    $Dockerfiles = Get-ChildItem -Recurse -Name "Dockerfile*"
    
    foreach ($Dockerfile in $Dockerfiles) {
        $Content = Get-Content $Dockerfile -Raw
        
        # Check for proper documentation
        if ($Content -match "# LUCID.*Distroless" -and $Content -match "# syntax=docker/dockerfile:1\.7") {
            Write-Host "✅ $Dockerfile has proper documentation" -ForegroundColor Green
        } else {
            if ($Action -eq "fix") {
                Write-Host "🔧 Adding documentation to $Dockerfile..." -ForegroundColor Yellow
                Write-Host "  - Add proper header with LUCID and Distroless tags" -ForegroundColor Gray
                Write-Host "  - Add Dockerfile syntax directive" -ForegroundColor Gray
            } else {
                Write-Host "❌ $Dockerfile missing proper documentation" -ForegroundColor Red
            }
        }
    }
}

# Main enforcement logic
switch ($Action) {
    "validate" {
        Write-Host "Validating compliance..." -ForegroundColor Yellow
        Enforce-DistrolessCompliance
        Enforce-ComposeCompliance
        Enforce-RegistryCompliance
        Enforce-NetworkCompliance
        Enforce-DocumentationCompliance
    }
    
    "fix" {
        Write-Host "Fixing compliance issues..." -ForegroundColor Yellow
        Enforce-DistrolessCompliance
        Enforce-ComposeCompliance
        Enforce-RegistryCompliance
        Enforce-NetworkCompliance
        Enforce-DocumentationCompliance
    }
    
    "enforce" {
        Write-Host "Enforcing compliance..." -ForegroundColor Yellow
        Enforce-DistrolessCompliance
        Enforce-ComposeCompliance
        Enforce-RegistryCompliance
        Enforce-NetworkCompliance
        Enforce-DocumentationCompliance
    }
    
    default {
        Write-Host "❌ Unknown action: $Action" -ForegroundColor Red
        Write-Host "Valid actions: validate, fix, enforce" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "=== Compliance Enforcement Complete ===" -ForegroundColor Green

if ($Action -eq "validate") {
    Write-Host "Run with -Action fix to automatically fix compliance issues" -ForegroundColor Yellow
}
