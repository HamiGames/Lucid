# Comprehensive Build Diagnostics Script
# Identifies all issues preventing successful devcontainer build
# Based on LUCID-STRICT mode requirements and Build_guide_docs specifications

Write-Host "===== Lucid DevContainer Build Diagnostics =====" -ForegroundColor Cyan

# Test 1: Docker System Health
Write-Host "Test 1: Docker system health..." -ForegroundColor Yellow
try {
    $dockerInfo = docker info --format "{{json .}}" | ConvertFrom-Json
    Write-Host "[+] Docker daemon running (version: $($dockerInfo.ServerVersion))" -ForegroundColor Green
    Write-Host "    Memory: $([math]::Round($dockerInfo.MemTotal/1GB, 1))GB available" -ForegroundColor White
    Write-Host "    Storage Driver: $($dockerInfo.Driver)" -ForegroundColor White
} catch {
    Write-Host "[-] Docker system issues detected" -ForegroundColor Red
    exit 1
}

# Test 2: Build Platform Requirements
Write-Host "Test 2: Build platform requirements..." -ForegroundColor Yellow
$requiredImages = @("python:3.12-slim", "mongo:7", "alpine:3.22.1")
foreach ($image in $requiredImages) {
    try {
        docker image inspect $image *>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[+] Base image available: $image" -ForegroundColor Green
        } else {
            Write-Host "[-] Base image missing: $image" -ForegroundColor Red
        }
    } catch {
        Write-Host "[-] Cannot check image: $image" -ForegroundColor Red
    }
}

# Test 3: BuildX Configuration
Write-Host "Test 3: BuildX configuration..." -ForegroundColor Yellow
try {
    $builders = docker buildx ls
    $lucidBuilder = $builders | Select-String "lucid_builder"
    if ($lucidBuilder) {
        Write-Host "[+] Lucid builder exists" -ForegroundColor Green
    } else {
        Write-Host "[-] Lucid builder not found" -ForegroundColor Red
        Write-Host "    Available builders:" -ForegroundColor Yellow
        docker buildx ls | Write-Host
    }
} catch {
    Write-Host "[-] BuildX not available" -ForegroundColor Red
}

# Test 4: Network Configuration
Write-Host "Test 4: Network configuration..." -ForegroundColor Yellow
try {
    docker network inspect lucid-dev_lucid_net *>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[+] Lucid network exists" -ForegroundColor Green
    } else {
        Write-Host "[-] Lucid network missing" -ForegroundColor Red
    }
} catch {
    Write-Host "[-] Network check failed" -ForegroundColor Red
}

# Test 5: File System Check
Write-Host "Test 5: File system check..." -ForegroundColor Yellow
$requiredFiles = @(
    ".devcontainer/Dockerfile",
    ".devcontainer/requirements-dev.txt", 
    "pyproject.toml",
    "build-devcontainer.ps1"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length
        Write-Host "[+] File exists: $file ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host "[-] File missing: $file" -ForegroundColor Red
    }
}

# Test 6: Build Context Analysis
Write-Host "Test 6: Build context analysis..." -ForegroundColor Yellow
try {
    $contextSize = (Get-ChildItem -Recurse | Measure-Object -Property Length -Sum).Sum
    $contextSizeMB = [math]::Round($contextSize / 1MB, 1)
    Write-Host "[+] Build context size: ${contextSizeMB}MB" -ForegroundColor Green
    
    if ($contextSizeMB -gt 500) {
        Write-Host "[!] Warning: Large build context may slow builds" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[-] Cannot analyze build context" -ForegroundColor Red
}

# Test 7: System Resources
Write-Host "Test 7: System resources..." -ForegroundColor Yellow
try {
    $memory = Get-WmiObject -Class Win32_ComputerSystem
    $totalMemoryGB = [math]::Round($memory.TotalPhysicalMemory / 1GB, 1)
    Write-Host "[+] System memory: ${totalMemoryGB}GB" -ForegroundColor Green
    
    $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
    $freeSpaceGB = [math]::Round($disk.FreeSpace / 1GB, 1)
    Write-Host "[+] Free disk space: ${freeSpaceGB}GB" -ForegroundColor Green
    
    if ($freeSpaceGB -lt 10) {
        Write-Host "[!] Warning: Low disk space may cause build failures" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[-] Cannot check system resources" -ForegroundColor Red
}

# Test 8: Build_guide_docs Compliance Check
Write-Host "Test 8: Build_guide_docs compliance..." -ForegroundColor Yellow
$specFiles = @(
    "Build_guide_docs/mode_LUCID-STRICT.md",
    "Build_guide_docs/Spec-1d.txt"
)

foreach ($specFile in $specFiles) {
    if (Test-Path $specFile) {
        Write-Host "[+] Spec file found: $specFile" -ForegroundColor Green
    } else {
        Write-Host "[-] Spec file missing: $specFile" -ForegroundColor Red
    }
}

# Test 9: Previous Build Artifacts
Write-Host "Test 9: Previous build artifacts..." -ForegroundColor Yellow
try {
    $images = docker images --filter "reference=pickme/lucid*" --format "{{.Repository}}:{{.Tag}} ({{.Size}})"
    if ($images) {
        Write-Host "[+] Found previous build artifacts:" -ForegroundColor Green
        $images | ForEach-Object { Write-Host "    $_" -ForegroundColor White }
    } else {
        Write-Host "[-] No previous build artifacts found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[-] Cannot check build artifacts" -ForegroundColor Red
}

# Test 10: Error Log Analysis
Write-Host "Test 10: Recent Docker errors..." -ForegroundColor Yellow
try {
    # Check Docker Desktop logs if accessible
    $dockerLogs = "$env:APPDATA\Docker\log\vm\"
    if (Test-Path $dockerLogs) {
        $recentLogs = Get-ChildItem $dockerLogs -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($recentLogs) {
            Write-Host "[+] Found Docker logs: $($recentLogs.Name)" -ForegroundColor Green
        }
    } else {
        Write-Host "[-] Docker logs not accessible" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[-] Cannot access Docker logs" -ForegroundColor Red
}

Write-Host ""
Write-Host "===== DIAGNOSTICS COMPLETE =====" -ForegroundColor Cyan
Write-Host "Review the issues above before running build fixes." -ForegroundColor Yellow