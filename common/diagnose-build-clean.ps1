# Comprehensive Build Diagnostics Script
# Identifies all issues preventing successful devcontainer build

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

# Test 2: BuildX Configuration
Write-Host "Test 2: BuildX configuration..." -ForegroundColor Yellow
try {
    $builders = docker buildx ls
    Write-Host "[+] Available builders:" -ForegroundColor Green
    docker buildx ls | Write-Host
} catch {
    Write-Host "[-] BuildX not available" -ForegroundColor Red
}

# Test 3: Network DNS Test
Write-Host "Test 3: Network DNS test..." -ForegroundColor Yellow
try {
    $result = nslookup registry-1.docker.io 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[+] Docker registry DNS resolution working" -ForegroundColor Green
    } else {
        Write-Host "[-] Docker registry DNS resolution failed" -ForegroundColor Red
    }
} catch {
    Write-Host "[-] DNS test failed" -ForegroundColor Red
}

# Test 4: File System Check
Write-Host "Test 4: File system check..." -ForegroundColor Yellow
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

# Test 5: System Resources
Write-Host "Test 5: System resources..." -ForegroundColor Yellow
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

# Test 6: Previous Build Artifacts
Write-Host "Test 6: Previous build artifacts..." -ForegroundColor Yellow
try {
    $images = docker images --filter "reference=pickme/lucid*" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
    if ($images.Count -gt 1) {
        Write-Host "[+] Found previous build artifacts:" -ForegroundColor Green
        Write-Host $images -ForegroundColor White
    } else {
        Write-Host "[-] No previous build artifacts found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[-] Cannot check build artifacts" -ForegroundColor Red
}

# Test 7: Pull Test
Write-Host "Test 7: Base image pull test..." -ForegroundColor Yellow
try {
    Write-Host "    Testing python:3.12-slim pull..." -ForegroundColor White
    docker pull python:3.12-slim 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[+] Successfully pulled python:3.12-slim" -ForegroundColor Green
    } else {
        Write-Host "[-] Failed to pull python:3.12-slim" -ForegroundColor Red
    }
} catch {
    Write-Host "[-] Pull test failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "===== DIAGNOSTICS COMPLETE =====" -ForegroundColor Cyan
Write-Host "Review the issues above before running build fixes." -ForegroundColor Yellow