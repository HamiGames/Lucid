# LUCID Dockerfile Analysis and Cleanup Script
# Analyzes all Dockerfiles in infrastructure/docker and identifies:
# 1. Which Dockerfiles are used by build scripts
# 2. Which are distroless compliant
# 3. Which are duplicates
# 4. Provides cleanup recommendations

param(
    [switch]$Cleanup = $false,
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param($Message, $Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"
    Write-Host $LogEntry
}

function Test-DistrolessCompliance {
    param([string]$DockerfilePath)
    
    try {
        $content = Get-Content $DockerfilePath -Raw
        $isDistroless = $false
        $hasMultiStage = $false
        $hasNonRoot = $false
        
        # Check for distroless base image
        if ($content -match "gcr\.io/distroless") {
            $isDistroless = $true
        }
        
        # Check for multi-stage build
        if ($content -match "FROM.*AS.*builder" -and $content -match "FROM.*distroless") {
            $hasMultiStage = $true
        }
        
        # Check for non-root user
        if ($content -match "USER\s+(nonroot|lucid|admin_user|auth_user)") {
            $hasNonRoot = $true
        }
        
        return @{
            IsDistroless = $isDistroless
            HasMultiStage = $hasMultiStage
            HasNonRoot = $hasNonRoot
            Compliant = $isDistroless -and $hasMultiStage -and $hasNonRoot
        }
    }
    catch {
        return @{
            IsDistroless = $false
            HasMultiStage = $false
            HasNonRoot = $false
            Compliant = $false
        }
    }
}

function Get-BuildScriptServices {
    # Extract services from build scripts
    $buildScriptServices = @()
    
    # From build-distroless-phases.ps1
    $buildScriptContent = Get-Content "build-distroless-phases.ps1" -Raw
    $matches = [regex]::Matches($buildScriptContent, '@{Name="([^"]+)";\s*Path="([^"]+)";\s*Dockerfile="([^"]+)"}')
    
    foreach ($match in $matches) {
        $buildScriptServices += @{
            Name = $match.Groups[1].Value
            Path = $match.Groups[2].Value
            Dockerfile = $match.Groups[3].Value
            FullPath = Join-Path $match.Groups[2].Value $match.Groups[3].Value
        }
    }
    
    return $buildScriptServices
}

# Main analysis
Write-Log "=== LUCID Dockerfile Analysis ===" "INFO"

# Get all Dockerfiles
$allDockerfiles = Get-ChildItem -Recurse -Path "infrastructure/docker" -Name "Dockerfile*" | ForEach-Object {
    $fullPath = Join-Path "infrastructure/docker" $_
    @{
        RelativePath = $_
        FullPath = $fullPath
        Directory = Split-Path $fullPath -Parent
        FileName = Split-Path $fullPath -Leaf
        Exists = Test-Path $fullPath
    }
}

Write-Log "Found $($allDockerfiles.Count) Dockerfiles" "INFO"

# Get services from build scripts
$buildScriptServices = Get-BuildScriptServices
Write-Log "Build scripts reference $($buildScriptServices.Count) services" "INFO"

# Analyze each Dockerfile
$analysis = @()
$duplicates = @()
$nonDistroless = @()
$unused = @()

foreach ($dockerfile in $allDockerfiles) {
    if (-not $dockerfile.Exists) {
        Write-Log "Dockerfile not found: $($dockerfile.FullPath)" "WARNING"
        continue
    }
    
    $compliance = Test-DistrolessCompliance -DockerfilePath $dockerfile.FullPath
    
    # Check if used by build scripts
    $usedByBuildScript = $buildScriptServices | Where-Object { 
        $_.FullPath -eq $dockerfile.RelativePath -or 
        $_.FullPath -eq $dockerfile.FullPath
    }
    
    $analysis += @{
        Dockerfile = $dockerfile
        Compliance = $compliance
        UsedByBuildScript = $usedByBuildScript.Count -gt 0
        BuildScriptService = $usedByBuildScript
    }
    
    # Categorize
    if (-not $compliance.Compliant) {
        $nonDistroless += $dockerfile
    }
    
    if (-not $usedByBuildScript) {
        $unused += $dockerfile
    }
}

# Find duplicates by filename
$duplicateGroups = $allDockerfiles | Group-Object FileName | Where-Object { $_.Count -gt 1 }

Write-Log "=== ANALYSIS RESULTS ===" "INFO"
Write-Log "Total Dockerfiles: $($allDockerfiles.Count)" "INFO"
Write-Log "Distroless Compliant: $(($analysis | Where-Object { $_.Compliance.Compliant }).Count)" "INFO"
Write-Log "Used by Build Scripts: $(($analysis | Where-Object { $_.UsedByBuildScript }).Count)" "INFO"
Write-Log "Unused Dockerfiles: $($unused.Count)" "INFO"
Write-Log "Duplicate Groups: $($duplicateGroups.Count)" "INFO"

# Report duplicates
if ($duplicateGroups.Count -gt 0) {
    Write-Log "=== DUPLICATE DOCKERFILES ===" "WARNING"
    foreach ($group in $duplicateGroups) {
        Write-Log "Duplicate: $($group.Name)" "WARNING"
        foreach ($file in $group.Group) {
            $compliance = Test-DistrolessCompliance -DockerfilePath $file.FullPath
            $status = if ($compliance.Compliant) { "DISTROLESS" } else { "NON-DISTROLESS" }
            Write-Log "  - $($file.RelativePath) [$status]" "WARNING"
        }
    }
}

# Report non-distroless files
if ($nonDistroless.Count -gt 0) {
    Write-Log "=== NON-DISTROLESS DOCKERFILES ===" "WARNING"
    foreach ($file in $nonDistroless) {
        $compliance = Test-DistrolessCompliance -DockerfilePath $file.FullPath
        Write-Log "  - $($file.RelativePath)" "WARNING"
        Write-Log "    Distroless: $($compliance.IsDistroless), Multi-stage: $($compliance.HasMultiStage), Non-root: $($compliance.HasNonRoot)" "WARNING"
    }
}

# Report unused files
if ($unused.Count -gt 0) {
    Write-Log "=== UNUSED DOCKERFILES ===" "INFO"
    foreach ($file in $unused) {
        Write-Log "  - $($file.RelativePath)" "INFO"
    }
}

# Build script path issues
Write-Log "=== BUILD SCRIPT PATH ISSUES ===" "WARNING"
foreach ($service in $buildScriptServices) {
    $expectedPath = Join-Path "infrastructure/docker" $service.FullPath
    if (-not (Test-Path $expectedPath)) {
        Write-Log "Missing: $($service.FullPath) (expected: $expectedPath)" "ERROR"
    }
}

# Cleanup recommendations
Write-Log "=== CLEANUP RECOMMENDATIONS ===" "INFO"

# Remove duplicate non-distroless files
$duplicatesToRemove = @()
foreach ($group in $duplicateGroups) {
    $distrolessFiles = $group.Group | Where-Object { 
        (Test-DistrolessCompliance -DockerfilePath $_.FullPath).Compliant 
    }
    $nonDistrolessFiles = $group.Group | Where-Object { 
        -not (Test-DistrolessCompliance -DockerfilePath $_.FullPath).Compliant 
    }
    
    if ($distrolessFiles.Count -gt 0 -and $nonDistrolessFiles.Count -gt 0) {
        $duplicatesToRemove += $nonDistrolessFiles
    }
}

if ($duplicatesToRemove.Count -gt 0) {
    Write-Log "Recommended for removal (duplicate non-distroless):" "INFO"
    foreach ($file in $duplicatesToRemove) {
        Write-Log "  - $($file.RelativePath)" "INFO"
    }
}

# Remove unused files
if ($unused.Count -gt 0) {
    Write-Log "Consider removing unused Dockerfiles:" "INFO"
    foreach ($file in $unused) {
        Write-Log "  - $($file.RelativePath)" "INFO"
    }
}

# Perform cleanup if requested
if ($Cleanup) {
    Write-Log "=== PERFORMING CLEANUP ===" "INFO"
    
    $removedCount = 0
    foreach ($file in $duplicatesToRemove) {
        try {
            Remove-Item $file.FullPath -Force
            Write-Log "Removed: $($file.RelativePath)" "SUCCESS"
            $removedCount++
        }
        catch {
            Write-Log "Failed to remove: $($file.RelativePath) - $($_.Exception.Message)" "ERROR"
        }
    }
    
    Write-Log "Cleanup completed. Removed $removedCount files." "SUCCESS"
}

Write-Log "=== ANALYSIS COMPLETE ===" "INFO"
