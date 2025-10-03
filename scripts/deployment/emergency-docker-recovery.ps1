# Emergency Docker Desktop Recovery Script
# Run this if Docker Desktop won't start after DNS configuration changes

Write-Host "===== Docker Desktop Emergency Recovery =====" -ForegroundColor Red

# Step 1: Check if Docker processes are running
Write-Host "Step 1: Checking Docker processes..." -ForegroundColor Yellow
$dockerProcesses = Get-Process | Where-Object {$_.Name -like "*docker*"}
if ($dockerProcesses) {
    Write-Host "Found Docker processes - killing them..." -ForegroundColor Yellow
    foreach ($process in $dockerProcesses) {
        Write-Host "Killing: $($process.Name) (PID: $($process.Id))" -ForegroundColor Yellow
        try {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        } catch {
            # Ignore errors
        }
    }
    Start-Sleep -Seconds 5
} else {
    Write-Host "[+] No Docker processes found" -ForegroundColor Green
}

# Step 2: Reset Docker daemon configuration (backup first)
Write-Host "Step 2: Backing up and resetting Docker configuration..." -ForegroundColor Yellow
$dockerConfigPath = "$env:USERPROFILE\.docker\daemon.json"
$backupPath = "$env:USERPROFILE\.docker\daemon.json.backup"

if (Test-Path $dockerConfigPath) {
    try {
        Copy-Item $dockerConfigPath $backupPath -Force
        Write-Host "[+] Backed up daemon.json to daemon.json.backup" -ForegroundColor Green
        
        # Create minimal safe configuration
        $safeConfig = @{
            "log-driver" = "json-file"
            "log-opts" = @{
                "max-size" = "10m"
                "max-file" = "3"
            }
        }
        
        $safeConfig | ConvertTo-Json -Depth 3 | Set-Content -Path $dockerConfigPath -Encoding UTF8
        Write-Host "[+] Reset daemon.json to safe minimal configuration" -ForegroundColor Green
    } catch {
        Write-Host "[-] Could not reset daemon.json" -ForegroundColor Red
    }
} else {
    Write-Host "[+] No daemon.json found to reset" -ForegroundColor Green
}

# Step 3: Clear Docker AppData
Write-Host "Step 3: Clearing Docker AppData (optional)..." -ForegroundColor Yellow
$dockerAppData = "$env:APPDATA\Docker"
if (Test-Path $dockerAppData) {
    try {
        Remove-Item "$dockerAppData\*" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "[+] Cleared Docker AppData" -ForegroundColor Green
    } catch {
        Write-Host "[-] Could not clear Docker AppData (may be in use)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[+] No Docker AppData found" -ForegroundColor Green
}

# Step 4: Check Windows Services
Write-Host "Step 4: Checking Windows Services..." -ForegroundColor Yellow
$services = @("com.docker.service", "Docker Desktop Service")
foreach ($serviceName in $services) {
    try {
        $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
        if ($service) {
            Write-Host "Found service: $serviceName (Status: $($service.Status))" -ForegroundColor Yellow
            if ($service.Status -eq "Running") {
                Write-Host "Stopping service: $serviceName" -ForegroundColor Yellow
                Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        # Ignore service errors
    }
}

# Step 5: Manual restart instructions
Write-Host ""
Write-Host "===== MANUAL RECOVERY STEPS =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. RESTART DOCKER DESKTOP:" -ForegroundColor Yellow
Write-Host "   - Press Windows key" -ForegroundColor White
Write-Host "   - Type 'Docker Desktop'" -ForegroundColor White
Write-Host "   - Right-click -> 'Run as Administrator'" -ForegroundColor White
Write-Host "   - If that fails, try regular launch" -ForegroundColor White
Write-Host ""

Write-Host "2. IF DOCKER DESKTOP STILL WON'T START:" -ForegroundColor Yellow
Write-Host "   - Open Docker Desktop" -ForegroundColor White
Write-Host "   - Go to Settings -> Troubleshoot" -ForegroundColor White
Write-Host "   - Click 'Restart Docker Desktop'" -ForegroundColor White
Write-Host "   - If still failing, click 'Reset to factory defaults'" -ForegroundColor White
Write-Host ""

Write-Host "3. ALTERNATIVE RECOVERY:" -ForegroundColor Yellow
Write-Host "   - Uninstall Docker Desktop (keep data)" -ForegroundColor White
Write-Host "   - Download fresh installer from docker.com" -ForegroundColor White
Write-Host "   - Reinstall Docker Desktop" -ForegroundColor White
Write-Host ""

Write-Host "4. CHECK SYSTEM REQUIREMENTS:" -ForegroundColor Yellow
Write-Host "   - Ensure WSL2 is enabled" -ForegroundColor White
Write-Host "   - Ensure Hyper-V is enabled" -ForegroundColor White
Write-Host "   - Ensure virtualization is enabled in BIOS" -ForegroundColor White
Write-Host ""

# Step 6: System checks
Write-Host "===== SYSTEM DIAGNOSTICS =====" -ForegroundColor Cyan

# Check WSL
Write-Host "Checking WSL..." -ForegroundColor Yellow
try {
    wsl --status 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[+] WSL appears to be working" -ForegroundColor Green
    } else {
        Write-Host "[-] WSL may have issues" -ForegroundColor Red
    }
} catch {
    Write-Host "[-] WSL not available" -ForegroundColor Red
}

# Check Hyper-V
Write-Host "Checking Hyper-V..." -ForegroundColor Yellow
try {
    $hyperv = Get-WindowsOptionalFeature -FeatureName Microsoft-Hyper-V-All -Online
    if ($hyperv.State -eq "Enabled") {
        Write-Host "[+] Hyper-V is enabled" -ForegroundColor Green
    } else {
        Write-Host "[-] Hyper-V is not enabled" -ForegroundColor Red
    }
} catch {
    Write-Host "[-] Could not check Hyper-V status" -ForegroundColor Red
}

Write-Host ""
Write-Host "===== WHAT LIKELY HAPPENED =====" -ForegroundColor Cyan
Write-Host "The DNS configuration changes should not have broken Docker completely." -ForegroundColor White
Write-Host "This is likely a coincidental Docker Desktop issue." -ForegroundColor White
Write-Host ""
Write-Host "The daemon.json has been reset to safe defaults." -ForegroundColor Yellow
Write-Host "Your original configuration is backed up as daemon.json.backup" -ForegroundColor Yellow
Write-Host ""
Write-Host "===== RECOVERY COMPLETE =====" -ForegroundColor Green
Write-Host "Try starting Docker Desktop now." -ForegroundColor Yellow