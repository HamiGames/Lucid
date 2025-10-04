# Docker Network Diagnostics and Fix Script
# Diagnoses and resolves Docker registry connectivity issues on Windows

Write-Host "===== Docker Network Diagnostics =====" -ForegroundColor Cyan

function Test-DockerDaemon {
    Write-Host "Testing Docker daemon..." -ForegroundColor Yellow
    try {
        $dockerInfo = docker info --format "{{.ServerVersion}}" 2>$null
        Write-Host "✓ Docker daemon running (version: $dockerInfo)" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "✗ Docker daemon not accessible" -ForegroundColor Red
        return $false
    }
}

function Test-NetworkConnectivity {
    Write-Host "Testing network connectivity..." -ForegroundColor Yellow
    
    # Test basic internet connectivity
    try {
        $response = Test-NetConnection -ComputerName "8.8.8.8" -Port 53 -InformationLevel Quiet
        if ($response) {
            Write-Host "[+] Basic internet connectivity working" -ForegroundColor Green
        } else {
            Write-Host "[-] No internet connectivity" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "[-] Network connectivity test failed" -ForegroundColor Red
        return $false
    }
    
    # Test Docker registry connectivity
    try {
        $response = Test-NetConnection -ComputerName "registry-1.docker.io" -Port 443 -InformationLevel Quiet
        if ($response) {
            Write-Host "[+] Docker registry reachable" -ForegroundColor Green
            return $true
        } else {
            Write-Host "[-] Docker registry not reachable" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "[-] Docker registry connectivity test failed" -ForegroundColor Red
        return $false
    }
}

function Test-DNSResolution {
    Write-Host "Testing DNS resolution..." -ForegroundColor Yellow
    
    $domains = @(
        "registry-1.docker.io",
        "index.docker.io",
        "docker.io",
        "production.cloudflare.docker.com"
    )
    
    foreach ($domain in $domains) {
        try {
            $result = Resolve-DnsName -Name $domain -ErrorAction Stop
            $ip = $result[0].IPAddress
            Write-Host "[+] DNS resolution for $domain`: $ip" -ForegroundColor Green
        } catch {
            Write-Host "[-] DNS resolution failed for $domain" -ForegroundColor Red
        }
    }
}

function Get-DockerConfiguration {
    Write-Host "Checking Docker configuration..." -ForegroundColor Yellow
    
    # Check Docker daemon configuration
    $dockerConfigPath = "$env:USERPROFILE\.docker\daemon.json"
    if (Test-Path $dockerConfigPath) {
        Write-Host "Found Docker daemon config at: $dockerConfigPath" -ForegroundColor Yellow
        try {
            $config = Get-Content $dockerConfigPath -Raw | ConvertFrom-Json
            Write-Host "Current configuration:" -ForegroundColor Yellow
            $config | ConvertTo-Json -Depth 3 | Write-Host
        } catch {
            Write-Host "[-] Could not parse Docker configuration" -ForegroundColor Red
        }
    } else {
        Write-Host "No Docker daemon configuration found" -ForegroundColor Yellow
    }
    
    # Check Docker Desktop settings
    Write-Host "Docker Desktop info:" -ForegroundColor Yellow
    try {
        docker system info 2>$null | Select-String "Registry" | Write-Host
    } catch {
        Write-Host "Could not retrieve Docker system info" -ForegroundColor Red
    }
}

function Fix-DockerDNS {
    Write-Host "Applying Docker DNS fixes..." -ForegroundColor Yellow
    
    $dockerConfigPath = "$env:USERPROFILE\.docker\daemon.json"
    $dockerConfigDir = Split-Path $dockerConfigPath -Parent
    
    # Create .docker directory if it doesn't exist
    if (-not (Test-Path $dockerConfigDir)) {
        New-Item -Path $dockerConfigDir -ItemType Directory -Force
        Write-Host "Created Docker config directory: $dockerConfigDir" -ForegroundColor Green
    }
    
    # Create or update daemon.json
    $daemonConfig = @{
        "dns" = @("8.8.8.8", "8.8.4.4", "1.1.1.1")
        "registry-mirrors" = @("https://mirror.gcr.io")
        "insecure-registries" = @()
        "log-driver" = "json-file"
        "log-opts" = @{
            "max-size" = "10m"
            "max-file" = "3"
        }
    }
    
    # If config exists, merge with existing settings
    if (Test-Path $dockerConfigPath) {
        try {
            $existingConfig = Get-Content $dockerConfigPath -Raw | ConvertFrom-Json
            
            # Preserve existing settings, override DNS
            foreach ($key in $existingConfig.PSObject.Properties.Name) {
                if ($key -ne "dns") {
                    $daemonConfig[$key] = $existingConfig.$key
                }
            }
        } catch {
            Write-Host "Warning: Could not parse existing Docker config, creating new one" -ForegroundColor Yellow
        }
    }
    
    # Write configuration
    $daemonConfig | ConvertTo-Json -Depth 3 | Set-Content -Path $dockerConfigPath -Encoding UTF8
    Write-Host "[+] Updated Docker daemon configuration" -ForegroundColor Green
    Write-Host "Configuration saved to: $dockerConfigPath" -ForegroundColor Yellow
    
    Write-Host "IMPORTANT: Restart Docker Desktop for changes to take effect!" -ForegroundColor Red
}

function Test-DockerPull {
    Write-Host "Testing Docker image pull..." -ForegroundColor Yellow
    
    # Test with a small image first
    try {
        Write-Host "Testing with hello-world image..." -ForegroundColor Yellow
        $result = docker pull hello-world 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[+] Successfully pulled hello-world image" -ForegroundColor Green
        } else {
            Write-Host "[-] Failed to pull hello-world image" -ForegroundColor Red
            return $false
        }
        
        # Test with Python base image
        Write-Host "Testing with Python 3.12-slim image..." -ForegroundColor Yellow
        $result = docker pull python:3.12-slim 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[+] Successfully pulled Python base image" -ForegroundColor Green
            return $true
        } else {
            Write-Host "[-] Failed to pull Python base image" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "[-] Failed to pull Docker images" -ForegroundColor Red
        return $false
    }
}

function Show-AdditionalSolutions {
    Write-Host "Additional Solutions:" -ForegroundColor Cyan
    Write-Host "1. Windows Firewall/Antivirus:" -ForegroundColor Yellow
    Write-Host "   - Temporarily disable Windows Defender/antivirus"
    Write-Host "   - Add Docker Desktop to firewall exceptions"
    Write-Host ""
    
    Write-Host "2. VPN/Proxy Issues:" -ForegroundColor Yellow
    Write-Host "   - Disconnect from VPN temporarily"
    Write-Host "   - Configure Docker Desktop proxy settings if needed"
    Write-Host ""
    
    Write-Host "3. Docker Desktop Reset:" -ForegroundColor Yellow
    Write-Host "   - Open Docker Desktop -> Settings -> Troubleshoot -> Reset to factory defaults"
    Write-Host "   - Restart Docker Desktop"
    Write-Host ""
    
    Write-Host "4. WSL2 Issues (if using WSL2 backend):" -ForegroundColor Yellow
    Write-Host "   - wsl --shutdown"
    Write-Host "   - Restart Docker Desktop"
    Write-Host ""
    
    Write-Host "5. Alternative Registry:" -ForegroundColor Yellow
    Write-Host "   - Use ghcr.io/library/python:3.12-slim instead"
    Write-Host "   - Configure registry mirrors in daemon.json"
}

# Main execution
Write-Host "Starting Docker network diagnostics..." -ForegroundColor Cyan
Write-Host ""

# Step 1: Test Docker daemon
if (-not (Test-DockerDaemon)) {
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Step 2: Test network connectivity
$networkOk = Test-NetworkConnectivity

# Step 3: Test DNS resolution  
Test-DNSResolution

# Step 4: Check Docker configuration
Get-DockerConfiguration

# Step 5: Apply fixes if network issues detected
if (-not $networkOk) {
    Write-Host ""
    Write-Host "Network issues detected. Applying fixes..." -ForegroundColor Yellow
    Fix-DockerDNS
    
    Write-Host ""
    Write-Host "Please restart Docker Desktop now and run this script again." -ForegroundColor Red
    exit 0
}

# Step 6: Test Docker pull
Write-Host ""
if (Test-DockerPull) {
    Write-Host ""
    Write-Host "✓ Docker networking appears to be working correctly!" -ForegroundColor Green
    Write-Host "You can now try building the devcontainer again." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Docker pull test failed. Additional troubleshooting needed." -ForegroundColor Red
    Show-AdditionalSolutions
}

Write-Host ""
Write-Host "===== Diagnostics Complete =====" -ForegroundColor Cyan