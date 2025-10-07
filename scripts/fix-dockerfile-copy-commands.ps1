# LUCID Dockerfile COPY Commands Fix Script
# Fixes all COPY commands in Dockerfiles to reference correct source paths

param(
    [switch]$DryRun = $false,
    [switch]$Force = $false,
    [string]$BackupDir = "backup_dockerfile_fixes_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
)

Write-Host "🔧 LUCID Dockerfile COPY Commands Fix Script" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
}

# Create backup directory if not dry run
if (-not $DryRun) {
    Write-Host "📦 Creating backup directory: $BackupDir" -ForegroundColor Blue
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

# Function to fix COPY commands in a Dockerfile
function Fix-DockerfileCopyCommands {
    param(
        [string]$DockerfilePath
    )
    
    if (-not (Test-Path $DockerfilePath)) {
        Write-Host "⚠️  Dockerfile not found: $DockerfilePath" -ForegroundColor Yellow
        return
    }
    
    Write-Host "🔧 Fixing COPY commands in: $DockerfilePath" -ForegroundColor Blue
    
    if (-not $DryRun) {
        # Create backup
        Copy-Item $DockerfilePath "$BackupDir/$(Split-Path $DockerfilePath -Leaf)" -Force
    }
    
    $content = Get-Content $DockerfilePath -Raw
    $originalContent = $content
    
    # Fix common incorrect COPY commands
    $fixes = @{
        # Blockchain fixes
        "COPY --chown=lucid:lucid app /app/app" = "COPY --chown=lucid:lucid blockchain/ /app/blockchain/"
        "COPY app /app/app" = "COPY blockchain/ /app/blockchain/"
        "COPY --chown=lucid:lucid app/ /app/app/" = "COPY --chown=lucid:lucid blockchain/ /app/blockchain/"
        
        # Sessions fixes
        "COPY sessions/ /app/sessions/" = "COPY sessions/ /app/sessions/"
        "COPY sessions/recorder/ /app/sessions/recorder/" = "COPY sessions/recorder/ /app/sessions/recorder/"
        
        # RDP fixes
        "COPY RDP/ /app/RDP/" = "COPY RDP/ /app/RDP/"
        "COPY RDP/recorder/ /app/RDP/recorder/" = "COPY RDP/recorder/ /app/RDP/recorder/"
        
        # Wallet fixes
        "COPY wallet/ /app/wallet/" = "COPY wallet/ /app/wallet/"
        "COPY wallet/walletd/ /app/wallet/walletd/" = "COPY wallet/walletd/ /app/wallet/walletd/"
        
        # Admin fixes
        "COPY admin/ /app/admin/" = "COPY admin/ /app/admin/"
        "COPY admin/admin-ui/ /app/admin/admin-ui/" = "COPY admin/admin-ui/ /app/admin/admin-ui/"
        "COPY admin/ui/ /app/admin/ui/" = "COPY admin/ui/ /app/admin/ui/"
        
        # Node fixes
        "COPY node/ /app/node/" = "COPY node/ /app/node/"
        "COPY node/consensus/ /app/node/consensus/" = "COPY node/consensus/ /app/node/consensus/"
        "COPY node/dht_crdt/ /app/node/dht_crdt/" = "COPY node/dht_crdt/ /app/node/dht_crdt/"
        
        # Common fixes
        "COPY common/ /app/common/" = "COPY common/ /app/common/"
        "COPY common/governance/ /app/common/governance/" = "COPY common/governance/ /app/common/governance/"
        "COPY common/server-tools/ /app/common/server-tools/" = "COPY common/server-tools/ /app/common/server-tools/"
        
        # Payment systems fixes
        "COPY payment-systems/ /app/payment-systems/" = "COPY payment-systems/ /app/payment-systems/"
        "COPY payment-systems/tron-node/ /app/payment-systems/tron-node/" = "COPY payment-systems/tron-node/ /app/payment-systems/tron-node/"
        
        # Tools fixes
        "COPY tools/ /app/tools/" = "COPY tools/ /app/tools/"
        "COPY tools/ops/ /app/tools/ops/" = "COPY tools/ops/ /app/tools/ops/"
        
        # Auth fixes
        "COPY auth/ /app/auth/" = "COPY auth/ /app/auth/"
    }
    
    # Apply fixes
    foreach ($incorrect in $fixes.Keys) {
        $correct = $fixes[$incorrect]
        if ($content -match [regex]::Escape($incorrect)) {
            $content = $content -replace [regex]::Escape($incorrect), $correct
            Write-Host "  ✅ Fixed: $incorrect -> $correct" -ForegroundColor Green
        }
    }
    
    # Check for any remaining issues
    if ($content -match "COPY.*app /app/app") {
        Write-Host "  ⚠️  Warning: Found potential issue with 'app /app/app' pattern" -ForegroundColor Yellow
    }
    
    if ($content -match "COPY.*app/ /app/app/") {
        Write-Host "  ⚠️  Warning: Found potential issue with 'app/ /app/app/' pattern" -ForegroundColor Yellow
    }
    
    # Save the fixed content
    if (-not $DryRun -and $content -ne $originalContent) {
        Set-Content -Path $DockerfilePath -Value $content -Encoding UTF8
        Write-Host "  ✅ Updated Dockerfile: $DockerfilePath" -ForegroundColor Green
    } elseif ($DryRun) {
        Write-Host "  🔍 Would update Dockerfile: $DockerfilePath" -ForegroundColor Cyan
    } else {
        Write-Host "  ℹ️  No changes needed for: $DockerfilePath" -ForegroundColor Gray
    }
}

# Get all Dockerfiles in both locations
$dockerfiles = @()

# Get Dockerfiles from dockerfiles/ directory
$dockerfiles += Get-ChildItem -Path "dockerfiles" -Recurse -Name "Dockerfile*" | ForEach-Object { "dockerfiles/$_" }

# Get Dockerfiles from infrastructure/docker/ directory
$dockerfiles += Get-ChildItem -Path "infrastructure/docker" -Recurse -Name "Dockerfile*" | ForEach-Object { "infrastructure/docker/$_" }

Write-Host "🔍 Found $($dockerfiles.Count) Dockerfiles to check" -ForegroundColor Blue

# Fix each Dockerfile
foreach ($dockerfile in $dockerfiles) {
    Fix-DockerfileCopyCommands -DockerfilePath $dockerfile
}

Write-Host "`n🎉 Dockerfile COPY commands fix complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

if (-not $DryRun) {
    Write-Host "📦 Backup created in: $BackupDir" -ForegroundColor Blue
    Write-Host "✅ All Dockerfile COPY commands have been fixed" -ForegroundColor Blue
} else {
    Write-Host "🔍 This was a dry run - no changes were made" -ForegroundColor Yellow
    Write-Host "🚀 Run with -Force to execute the fixes" -ForegroundColor Blue
}
