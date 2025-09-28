# Quick Docker DNS Fix Script for Lucid RDP Development
# Based on WARP.md project objectives and LUCID-STRICT requirements
# Addresses core DNS resolution timeout issue

Write-Host "===== Lucid Docker DNS Fix =====" -ForegroundColor Cyan

# Step 1: Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Yellow
try {
    docker info *>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[-] Docker is not running. Please start Docker Desktop." -ForegroundColor Red
        exit 1
    }
    Write-Host "[+] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "[-] Docker is not accessible. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Step 2: Create Docker config directory
$dockerConfigDir = "$env:USERPROFILE\.docker"
$dockerConfigPath = "$dockerConfigDir\daemon.json"

Write-Host "Creating Docker configuration..." -ForegroundColor Yellow
if (-not (Test-Path $dockerConfigDir)) {
    New-Item -Path $dockerConfigDir -ItemType Directory -Force | Out-Null
    Write-Host "[+] Created Docker config directory" -ForegroundColor Green
}

# Step 3: Configure Docker DNS settings
$daemonConfig = @{
    "dns" = @("8.8.8.8", "8.8.4.4", "1.1.1.1")
    "registry-mirrors" = @("https://mirror.gcr.io")
    "log-driver" = "json-file"
    "log-opts" = @{
        "max-size" = "10m"
        "max-file" = "3"
    }
}

# Merge with existing config if present
if (Test-Path $dockerConfigPath) {
    try {
        $existingConfig = Get-Content $dockerConfigPath -Raw | ConvertFrom-Json
        # Preserve non-DNS settings
        foreach ($key in $existingConfig.PSObject.Properties.Name) {
            if ($key -notin @("dns", "registry-mirrors")) {
                $daemonConfig[$key] = $existingConfig.$key
            }
        }
        Write-Host "[+] Merged with existing Docker configuration" -ForegroundColor Green
    } catch {
        Write-Host "Warning: Could not parse existing config, creating new one" -ForegroundColor Yellow
    }
}

# Write configuration
$daemonConfig | ConvertTo-Json -Depth 3 | Set-Content -Path $dockerConfigPath -Encoding UTF8
Write-Host "[+] Updated Docker daemon configuration" -ForegroundColor Green

# Step 4: Test DNS resolution
Write-Host "Testing DNS resolution..." -ForegroundColor Yellow
$testDomains = @("registry-1.docker.io", "docker.io")
$dnsWorking = $true

foreach ($domain in $testDomains) {
    try {
        $result = Resolve-DnsName -Name $domain -ErrorAction Stop
        Write-Host "[+] DNS resolution for $domain`: $($result[0].IPAddress)" -ForegroundColor Green
    } catch {
        Write-Host "[-] DNS resolution failed for $domain" -ForegroundColor Red
        $dnsWorking = $false
    }
}

if ($dnsWorking) {
    Write-Host "[+] DNS resolution is working" -ForegroundColor Green
} else {
    Write-Host "[-] DNS issues detected" -ForegroundColor Red
}

# Step 5: Instructions
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "1. RESTART Docker Desktop (Essential!)" -ForegroundColor Red
Write-Host "2. Wait for Docker to fully start" -ForegroundColor Yellow
Write-Host "3. Test with: docker pull hello-world" -ForegroundColor Yellow
Write-Host "4. Then run: .\build-devcontainer.ps1 -TestOnly" -ForegroundColor Yellow

Write-Host ""
Write-Host "If issues persist:" -ForegroundColor Yellow
Write-Host "- Temporarily disable Windows Defender" -ForegroundColor White
Write-Host "- Disconnect from VPN if connected" -ForegroundColor White
Write-Host "- Check Windows Firewall settings" -ForegroundColor White

Write-Host ""
Write-Host "Configuration saved to: $dockerConfigPath" -ForegroundColor Green
Write-Host "===== Fix Applied =====" -ForegroundColor Cyan