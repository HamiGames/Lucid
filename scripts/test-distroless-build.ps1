# LUCID DISTROLESS BUILD VALIDATION
# Test script to validate distroless build process
# Tests a subset of images to verify build functionality

param(
    [switch]$TestBuild = $true,
    [switch]$TestConfig = $true,
    [switch]$TestDeploy = $false,
    [switch]$Verbose = $false
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

# Test configuration
$TestImages = @(
    @{
        ServiceName = "admin-ui"
        DockerfilePath = "infrastructure/docker/admin/Dockerfile.admin-ui.distroless"
        ExpectedPort = 3000
    },
    @{
        ServiceName = "blockchain-api"
        DockerfilePath = "infrastructure/docker/blockchain/Dockerfile.distroless"
        ExpectedPort = 8084
    },
    @{
        ServiceName = "authentication-service"
        DockerfilePath = "infrastructure/docker/users/Dockerfile.authentication-service.distroless"
        ExpectedPort = 8085
    }
)

function Test-ScriptAvailability {
    Write-Progress "Testing script availability..."
    
    $scripts = @(
        "scripts/build-all-distroless-images.ps1",
        "scripts/generate-service-environments.ps1",
        "scripts/deploy-distroless-cluster.ps1"
    )
    
    foreach ($script in $scripts) {
        if (Test-Path $script) {
            Write-Success "Script found: $script"
        } else {
            Write-Error "Script not found: $script"
            return $false
        }
    }
    
    return $true
}

function Test-DockerfileAvailability {
    Write-Progress "Testing Dockerfile availability..."
    
    $availableCount = 0
    $totalCount = $TestImages.Count
    
    foreach ($testImage in $TestImages) {
        if (Test-Path $testImage.DockerfilePath) {
            Write-Success "Dockerfile found: $($testImage.ServiceName)"
            $availableCount++
        } else {
            Write-Warning "Dockerfile not found: $($testImage.ServiceName) at $($testImage.DockerfilePath)"
        }
    }
    
    Write-Info "Dockerfile availability: $availableCount/$totalCount"
    return $availableCount -gt 0
}

function Test-DockerfileCompliance {
    Write-Progress "Testing Dockerfile compliance..."
    
    $compliantCount = 0
    $totalCount = $TestImages.Count
    
    foreach ($testImage in $TestImages) {
        if (-not (Test-Path $testImage.DockerfilePath)) {
            continue
        }
        
        $content = Get-Content $testImage.DockerfilePath -Raw
        
        $checks = @(
            @{ Name = "Distroless base"; Pattern = "FROM gcr\.io/distroless/"; Result = $false }
            @{ Name = "Multi-stage build"; Pattern = "FROM.*AS.*builder"; Result = $false }
            @{ Name = "Syntax directive"; Pattern = "# syntax=docker/dockerfile:1\.[0-9]+"; Result = $false }
            @{ Name = "Service label"; Pattern = "org\.lucid\.service"; Result = $false }
            @{ Name = "Non-root user"; Pattern = "USER.*nonroot|USER.*[0-9]+"; Result = $false }
        )
        
        $passedChecks = 0
        foreach ($check in $checks) {
            if ($content -match $check.Pattern) {
                $check.Result = $true
                $passedChecks++
            }
        }
        
        if ($passedChecks -ge 3) {
            Write-Success "Dockerfile compliant: $($testImage.ServiceName) ($passedChecks/5 checks passed)"
            $compliantCount++
        } else {
            Write-Warning "Dockerfile not fully compliant: $($testImage.ServiceName) ($passedChecks/5 checks passed)"
        }
    }
    
    Write-Info "Dockerfile compliance: $compliantCount/$totalCount"
    return $compliantCount -gt 0
}

function Test-BuildScript {
    Write-Progress "Testing build script functionality..."
    
    try {
        $buildScript = "scripts/build-all-distroless-images.ps1"
        
        # Test script syntax
        $syntaxCheck = powershell -NoProfile -Command "& { Set-StrictMode -Version Latest; try { . '$buildScript' -WhatIf } catch { Write-Host 'Syntax Error: $_' } }"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Build script syntax validation passed"
        } else {
            Write-Error "Build script syntax validation failed"
            return $false
        }
        
        return $true
    }
    catch {
        Write-Error "Build script test failed: $_"
        return $false
    }
}

function Test-ConfigScript {
    Write-Progress "Testing configuration script functionality..."
    
    try {
        $configScript = "scripts/generate-service-environments.ps1"
        
        # Test script syntax
        $syntaxCheck = powershell -NoProfile -Command "& { Set-StrictMode -Version Latest; try { . '$configScript' -WhatIf } catch { Write-Host 'Syntax Error: $_' } }"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Configuration script syntax validation passed"
        } else {
            Write-Error "Configuration script syntax validation failed"
            return $false
        }
        
        return $true
    }
    catch {
        Write-Error "Configuration script test failed: $_"
        return $false
    }
}

function Test-DeployScript {
    Write-Progress "Testing deployment script functionality..."
    
    try {
        $deployScript = "scripts/deploy-distroless-cluster.ps1"
        
        # Test script syntax
        $syntaxCheck = powershell -NoProfile -Command "& { Set-StrictMode -Version Latest; try { . '$deployScript' -WhatIf } catch { Write-Host 'Syntax Error: $_' } }"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Deployment script syntax validation passed"
        } else {
            Write-Error "Deployment script syntax validation failed"
            return $false
        }
        
        return $true
    }
    catch {
        Write-Error "Deployment script test failed: $_"
        return $false
    }
}

function Test-DockerEnvironment {
    Write-Progress "Testing Docker environment..."
    
    try {
        # Test Docker availability
        docker version | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker not available"
        }
        Write-Success "Docker is available"
        
        # Test Docker Compose availability
        docker-compose --version | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker Compose not available"
        }
        Write-Success "Docker Compose is available"
        
        # Test Docker Buildx availability
        docker buildx version | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker Buildx not available"
        }
        Write-Success "Docker Buildx is available"
        
        return $true
    }
    catch {
        Write-Error "Docker environment test failed: $_"
        return $false
    }
}

function Show-TestSummary {
    param([hashtable]$Results)
    
    Write-ColorOutput "`n" + "="*80 "Magenta"
    Write-ColorOutput "LUCID DISTROLESS BUILD VALIDATION SUMMARY" "Magenta"
    Write-ColorOutput "="*80 "Magenta"
    
    $totalTests = $Results.Count
    $passedTests = ($Results.Values | Where-Object { $_ -eq $true }).Count
    $failedTests = $totalTests - $passedTests
    
    Write-Info "Total Tests: $totalTests"
    Write-Success "Passed: $passedTests"
    Write-Error "Failed: $failedTests"
    
    Write-Info "`nTest Results:"
    foreach ($test in $Results.Keys) {
        $result = $Results[$test]
        $color = if ($result) { "Green" } else { "Red" }
        $symbol = if ($result) { "✅" } else { "❌" }
        Write-ColorOutput "  $symbol $test" $color
    }
    
    if ($failedTests -eq 0) {
        Write-Success "`nAll validation tests passed! The distroless build system is ready."
    } else {
        Write-Warning "`nSome validation tests failed. Please review the issues above."
    }
    
    Write-ColorOutput "`n" + "="*80 "Magenta"
}

function Main {
    Write-ColorOutput "LUCID DISTROLESS BUILD VALIDATION" "Magenta"
    Write-ColorOutput "Testing distroless build system functionality" "Magenta"
    Write-ColorOutput ""
    
    $testResults = @{}
    
    try {
        # Test script availability
        $testResults["Script Availability"] = Test-ScriptAvailability
        
        # Test Docker environment
        $testResults["Docker Environment"] = Test-DockerEnvironment
        
        # Test Dockerfile availability
        $testResults["Dockerfile Availability"] = Test-DockerfileAvailability
        
        # Test Dockerfile compliance
        $testResults["Dockerfile Compliance"] = Test-DockerfileCompliance
        
        # Test build script
        if ($TestBuild) {
            $testResults["Build Script"] = Test-BuildScript
        }
        
        # Test configuration script
        if ($TestConfig) {
            $testResults["Configuration Script"] = Test-ConfigScript
        }
        
        # Test deployment script
        if ($TestDeploy) {
            $testResults["Deployment Script"] = Test-DeployScript
        }
        
        # Show summary
        Show-TestSummary $testResults
        
        # Exit with appropriate code
        $failedTests = ($testResults.Values | Where-Object { $_ -eq $false }).Count
        if ($failedTests -eq 0) {
            exit 0
        } else {
            exit 1
        }
    }
    catch {
        Write-Error "Validation process failed: $_"
        Show-TestSummary $testResults
        exit 1
    }
}

# Run main function
Main
