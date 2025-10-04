# LUCID SSH KEY SETUP - Eliminate Passphrase Prompts
# Sets up passwordless SSH authentication to Pi
# Usage: .\scripts\deployment\setup-ssh-key.ps1

param(
    [string]$PiHost = "192.168.0.75",
    [string]$PiUser = "pickme"
)

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "LUCID SSH KEY SETUP - Passwordless Authentication" -ForegroundColor Cyan
Write-Host "Target: $PiUser@$PiHost" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan

Write-Host "`n[1/3] CHECKING EXISTING SSH KEYS" -ForegroundColor Green

$sshKeyPath = "$env:USERPROFILE\.ssh\id_rsa.pub"

if (Test-Path $sshKeyPath) {
    Write-Host "  -> SSH public key found: $sshKeyPath" -ForegroundColor White
    $publicKey = Get-Content $sshKeyPath
    Write-Host "    Key: $($publicKey.Substring(0, 50))..." -ForegroundColor Gray
} else {
    Write-Host "  -> No SSH key found, generating new one..." -ForegroundColor White
    
    # Generate SSH key without passphrase
    Write-Host "    Generating SSH key (no passphrase)..." -ForegroundColor Gray
    ssh-keygen -t rsa -b 4096 -f "$env:USERPROFILE\.ssh\id_rsa" -N "" -C "lucid-deployment@$(hostname)"
    
    if (Test-Path $sshKeyPath) {
        Write-Host "    Check SSH key generated successfully" -ForegroundColor Gray
        $publicKey = Get-Content $sshKeyPath
    } else {
        Write-Error "Failed to generate SSH key"
        exit 1
    }
}

Write-Host "`n[2/3] COPYING SSH KEY TO PI" -ForegroundColor Green
Write-Host "  -> This will prompt for the Pi password one time" -ForegroundColor Yellow

try {
    # Copy SSH key to Pi (will prompt for password)
    $publicKey | ssh $PiUser@$PiHost "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    Check SSH key copied to Pi successfully" -ForegroundColor Gray
    } else {
        throw "SSH key copy failed"
    }
}
catch {
    Write-Error "Failed to copy SSH key to Pi: $($_.Message)"
    Write-Host "Manual setup:" -ForegroundColor Yellow
    Write-Host "  1. ssh $PiUser@$PiHost" -ForegroundColor White
    Write-Host "  2. mkdir -p ~/.ssh" -ForegroundColor White
    Write-Host "  3. Add your public key to ~/.ssh/authorized_keys" -ForegroundColor White
    exit 1
}

Write-Host "`n[3/3] TESTING PASSWORDLESS SSH" -ForegroundColor Green

try {
    $testResult = ssh -o StrictHostKeyChecking=no $PiUser@$PiHost "echo 'PASSWORDLESS_SSH_OK'"
    
    if ($testResult -match "PASSWORDLESS_SSH_OK") {
        Write-Host "  Check Passwordless SSH working!" -ForegroundColor Green
        Write-Host "`n==============================================================================" -ForegroundColor Cyan
        Write-Host "SUCCESS SSH Key Setup Complete!" -ForegroundColor Green
        Write-Host "You can now run deployment scripts without password prompts:" -ForegroundColor Green
        Write-Host "  .\scripts\deployment\deploy-to-pi-enhanced.ps1 -TorProxyOnly" -ForegroundColor White
        Write-Host "==============================================================================" -ForegroundColor Cyan
    } else {
        throw "SSH test failed"
    }
}
catch {
    Write-Warning "SSH key setup may not be working correctly"
    Write-Host "Try manual SSH test: ssh $PiUser@$PiHost" -ForegroundColor Yellow
}

exit 0