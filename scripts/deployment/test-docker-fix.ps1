# Test Docker DNS Fix - Verification Script
# Run this AFTER restarting Docker Desktop

Write-Host "===== Testing Docker DNS Fix =====" -ForegroundColor Cyan

# Test 1: Docker daemon health
Write-Host "Test 1: Docker daemon health..." -ForegroundColor Yellow
try {
    docker info *>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[+] Docker daemon is running" -ForegroundColor Green
    } else {
        Write-Host "[-] Docker daemon not ready" -ForegroundColor Red
        Write-Host "Please ensure Docker Desktop is fully started (green whale icon)" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "[-] Docker daemon not accessible" -ForegroundColor Red
    exit 1
}

# Test 2: DNS resolution
Write-Host "Test 2: DNS resolution..." -ForegroundColor Yellow
$dnsSuccess = $true
$testDomains = @("registry-1.docker.io", "docker.io", "index.docker.io")

foreach ($domain in $testDomains) {
    try {
        $result = Resolve-DnsName -Name $domain -ErrorAction Stop
        Write-Host "[+] DNS OK: $domain -> $($result[0].IPAddress)" -ForegroundColor Green
    } catch {
        Write-Host "[-] DNS FAIL: $domain" -ForegroundColor Red
        $dnsSuccess = $false
    }
}

if (-not $dnsSuccess) {
    Write-Host "[-] DNS resolution issues detected" -ForegroundColor Red
    Write-Host "Try: Restart Docker Desktop again or check Windows Firewall" -ForegroundColor Yellow
    exit 1
}

# Test 3: Image pull (small image)
Write-Host "Test 3: Docker image pull..." -ForegroundColor Yellow
try {
    Write-Host "Pulling hello-world image..." -ForegroundColor Yellow
    $pullResult = docker pull hello-world 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[+] Successfully pulled hello-world image" -ForegroundColor Green
    } else {
        Write-Host "[-] Failed to pull hello-world image" -ForegroundColor Red
        Write-Host "Error: $pullResult" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[-] Image pull failed" -ForegroundColor Red
    exit 1
}

# Test 4: Python base image (the one causing original issue)
Write-Host "Test 4: Python base image pull..." -ForegroundColor Yellow
try {
    Write-Host "Pulling python:3.12-slim image..." -ForegroundColor Yellow
    $pullResult = docker pull python:3.12-slim 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[+] Successfully pulled python:3.12-slim image" -ForegroundColor Green
    } else {
        Write-Host "[-] Failed to pull python:3.12-slim image" -ForegroundColor Red
        Write-Host "Error: $pullResult" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[-] Python base image pull failed" -ForegroundColor Red
    exit 1
}

# Success summary
Write-Host ""
Write-Host "===== ALL TESTS PASSED! =====" -ForegroundColor Green
Write-Host "[+] Docker daemon is healthy" -ForegroundColor Green
Write-Host "[+] DNS resolution is working" -ForegroundColor Green  
Write-Host "[+] Image pulling is working" -ForegroundColor Green
Write-Host "[+] Python base image pulls successfully" -ForegroundColor Green

Write-Host ""
Write-Host "Docker DNS fix is working! You can now:" -ForegroundColor Cyan
Write-Host "1. Build the devcontainer: .\build-devcontainer.ps1 -TestOnly" -ForegroundColor Yellow
Write-Host "2. Or run the full build: .\build-devcontainer.ps1" -ForegroundColor Yellow

Write-Host ""
Write-Host "===== Fix Verified Successfully =====" -ForegroundColor Cyan