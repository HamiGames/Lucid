# LUCID PROJECT - COMMIT AND PUSH ALL CHANGES TO GITHUB
# Generated: 2025-10-04 11:33:18 UTC
# Repository: HamiGames/Lucid.git
# Mode: LUCID-STRICT compliant

[CmdletBinding()]
param(
    [string]$CommitMessage = "Deploy: Rebuild lucid-devcontainer, Pi SSH commands, and progress tracking - SPEC-4 compliant",
    [switch]$DryRun = $false,
    [switch]$Force = $false,
    [switch]$SkipPush = $false,
    [switch]$Help = $false
)

if ($Help) {
    Write-Host @"
LUCID PROJECT - COMMIT AND PUSH SCRIPT
======================================

USAGE:
    .\commit-and-push-changes.ps1 [OPTIONS]

OPTIONS:
    -CommitMessage <string>    Custom commit message (default: auto-generated)
    -DryRun                   Show what would be committed without making changes
    -Force                    Force push to remote (use with caution)
    -SkipPush                 Commit locally but don't push to remote
    -Help                     Show this help message

EXAMPLES:
    .\commit-and-push-changes.ps1
    .\commit-and-push-changes.ps1 -DryRun
    .\commit-and-push-changes.ps1 -CommitMessage "Custom deployment message" -Force
    .\commit-and-push-changes.ps1 -SkipPush

REPOSITORY: HamiGames/Lucid.git
BRANCH: main (or current branch)
"@
    exit 0
}

# Color and formatting functions
function Write-StatusMessage {
    param($Message, $Type = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    switch ($Type) {
        "SUCCESS" { Write-Host "[$timestamp] [+] $Message" -ForegroundColor Green }
        "ERROR"   { Write-Host "[$timestamp] [!] $Message" -ForegroundColor Red }
        "WARNING" { Write-Host "[$timestamp] [-] $Message" -ForegroundColor Yellow }
        "INFO"    { Write-Host "[$timestamp] [i] $Message" -ForegroundColor Cyan }
        default   { Write-Host "[$timestamp] $Message" }
    }
}

function Write-Header {
    param($Title)
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Magenta
    Write-Host " $Title" -ForegroundColor Magenta
    Write-Host "=" * 70 -ForegroundColor Magenta
    Write-Host ""
}

# Error handling
$ErrorActionPreference = "Stop"
trap {
    Write-StatusMessage "CRITICAL ERROR: $($_.Exception.Message)" "ERROR"
    Write-StatusMessage "Script execution failed at line $($_.InvocationInfo.ScriptLineNumber)" "ERROR"
    exit 1
}

Write-Header "LUCID PROJECT - GIT COMMIT AND PUSH OPERATIONS"

# Verify we're in the correct directory
Write-StatusMessage "Verifying project directory..." "INFO"
if (-not (Test-Path ".git") -or -not (Test-Path "infrastructure")) {
    Write-StatusMessage "ERROR: Not in Lucid project root directory!" "ERROR"
    Write-StatusMessage "Please run this script from the Lucid project root." "ERROR"
    exit 1
}

Write-StatusMessage "Project directory verified: $(Get-Location)" "SUCCESS"

# Check Git status
Write-StatusMessage "Checking Git repository status..." "INFO"
try {
    $gitStatus = git status --porcelain
    if ($gitStatus) {
        Write-StatusMessage "Found changes to commit:" "INFO"
        git status --short
    } else {
        Write-StatusMessage "No changes detected in repository" "WARNING"
        if (-not $Force) {
            Write-StatusMessage "Use -Force to proceed anyway" "INFO"
            exit 0
        }
    }
} catch {
    Write-StatusMessage "Failed to check Git status: $($_.Exception.Message)" "ERROR"
    exit 1
}

# Get current branch
Write-StatusMessage "Detecting current Git branch..." "INFO"
try {
    $currentBranch = git rev-parse --abbrev-ref HEAD
    Write-StatusMessage "Current branch: $currentBranch" "SUCCESS"
} catch {
    Write-StatusMessage "Failed to detect current branch: $($_.Exception.Message)" "ERROR"
    exit 1
}

# Show files to be committed
Write-StatusMessage "Files to be committed:" "INFO"
Write-Host ""
Write-Host "MODIFIED/NEW FILES:" -ForegroundColor Yellow
Write-Host "-" * 50 -ForegroundColor Yellow

# List specific files we've created/modified
$filesToCommit = @(
    "scripts/deployment/rebuild-lucid-devcontainer-optimized.ps1",
    "scripts/deployment/quick-rebuild-devcontainer.ps1",
    "scripts/deployment/commit-and-push-changes.ps1",
    "progress/LUCID_PROJECT_COMPLETE_FILE_TREE_2025-10-04.md",
    "progress/LUCID_BUILD_PROGRESS_TRACKING_2025-10-04.md",
    "progress/PI_SSH_DEPLOYMENT_COMMANDS_2025-10-04.md"
)

foreach ($file in $filesToCommit) {
    if (Test-Path $file) {
        $status = if (git ls-files --error-unmatch $file 2>$null) { "MODIFIED" } else { "NEW" }
        Write-Host "  [$status] $file" -ForegroundColor $(if ($status -eq "NEW") { "Green" } else { "Yellow" })
    }
}

# Show any other modified files
Write-Host ""
Write-Host "OTHER CHANGES:" -ForegroundColor Cyan
Write-Host "-" * 50 -ForegroundColor Cyan
$otherChanges = git status --porcelain | Where-Object { 
    $line = $_.Substring(3)  # Remove status prefix
    $line -notin $filesToCommit
}

if ($otherChanges) {
    $otherChanges | ForEach-Object {
        $status = $_.Substring(0,2).Trim()
        $file = $_.Substring(3)
        Write-Host "  [$status] $file" -ForegroundColor White
    }
} else {
    Write-Host "  No other changes detected" -ForegroundColor Gray
}

Write-Host ""

# Dry run mode
if ($DryRun) {
    Write-StatusMessage "DRY RUN MODE - No changes will be made" "WARNING"
    Write-Host ""
    Write-Host "WOULD EXECUTE:" -ForegroundColor Yellow
    Write-Host "  git add ." -ForegroundColor Gray
    Write-Host "  git commit -m `"$CommitMessage`"" -ForegroundColor Gray
    if (-not $SkipPush) {
        $pushCmd = "git push origin $currentBranch"
        if ($Force) { $pushCmd += " --force" }
        Write-Host "  $pushCmd" -ForegroundColor Gray
    }
    Write-Host ""
    Write-StatusMessage "Dry run completed - no actual changes made" "INFO"
    exit 0
}

# Confirmation prompt (unless Force is used)
if (-not $Force) {
    Write-Host ""
    Write-Host "COMMIT DETAILS:" -ForegroundColor Magenta
    Write-Host "  Branch: $currentBranch" -ForegroundColor White
    Write-Host "  Message: $CommitMessage" -ForegroundColor White
    Write-Host "  Push to remote: $(-not $SkipPush)" -ForegroundColor White
    Write-Host ""
    
    $confirm = Read-Host "Proceed with commit and push? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-StatusMessage "Operation cancelled by user" "WARNING"
        exit 0
    }
}

Write-Header "EXECUTING GIT OPERATIONS"

# Stage all changes
Write-StatusMessage "Staging all changes..." "INFO"
try {
    git add .
    Write-StatusMessage "All changes staged successfully" "SUCCESS"
} catch {
    Write-StatusMessage "Failed to stage changes: $($_.Exception.Message)" "ERROR"
    exit 1
}

# Commit changes
Write-StatusMessage "Committing changes..." "INFO"
try {
    git commit -m $CommitMessage
    Write-StatusMessage "Changes committed successfully" "SUCCESS"
} catch {
    Write-StatusMessage "Failed to commit changes: $($_.Exception.Message)" "ERROR"
    Write-StatusMessage "This might be because there are no changes to commit" "INFO"
}

# Push to remote (if not skipped)
if (-not $SkipPush) {
    Write-StatusMessage "Pushing to remote repository..." "INFO"
    try {
        $pushArgs = @("push", "origin", $currentBranch)
        if ($Force) {
            $pushArgs += "--force"
            Write-StatusMessage "WARNING: Using force push!" "WARNING"
        }
        
        git @pushArgs
        Write-StatusMessage "Changes pushed to remote successfully" "SUCCESS"
        
        # Show remote URL
        $remoteUrl = git config --get remote.origin.url
        Write-StatusMessage "Remote repository: $remoteUrl" "INFO"
        
    } catch {
        Write-StatusMessage "Failed to push changes: $($_.Exception.Message)" "ERROR"
        Write-StatusMessage "Local commit was successful, but remote push failed" "WARNING"
        Write-StatusMessage "You may need to pull changes first or use -Force" "INFO"
        exit 1
    }
} else {
    Write-StatusMessage "Skipping push to remote (as requested)" "WARNING"
}

# Final verification
Write-Header "FINAL VERIFICATION"

Write-StatusMessage "Verifying final Git status..." "INFO"
try {
    $finalStatus = git status --porcelain
    if (-not $finalStatus) {
        Write-StatusMessage "Repository is clean - all changes committed" "SUCCESS"
    } else {
        Write-StatusMessage "Some files remain uncommitted:" "WARNING"
        git status --short
    }
} catch {
    Write-StatusMessage "Failed to verify final status: $($_.Exception.Message)" "ERROR"
}

# Show recent commits
Write-StatusMessage "Recent commits:" "INFO"
Write-Host ""
try {
    git log --oneline -5 --color=always
} catch {
    Write-StatusMessage "Failed to show recent commits: $($_.Exception.Message)" "WARNING"
}

Write-Header "DEPLOYMENT COMMIT COMPLETED"

Write-StatusMessage "All Git operations completed successfully!" "SUCCESS"
Write-StatusMessage "Repository: HamiGames/Lucid.git" "INFO"
Write-StatusMessage "Branch: $currentBranch" "INFO"

if (-not $SkipPush) {
    Write-StatusMessage "Changes are now live in the remote repository" "SUCCESS"
    Write-StatusMessage "Pi deployment can proceed with: git pull origin main" "INFO"
} else {
    Write-StatusMessage "Changes committed locally only" "WARNING"
    Write-StatusMessage "Run 'git push origin $currentBranch' to push to remote" "INFO"
}

Write-Host ""
Write-StatusMessage "LUCID project deployment commit script completed!" "SUCCESS"