<#  bootstrap-dev.ps1
    Purpose: Deterministic Windows dev rebuild/launch for the Lucid stack.
    Fixes: inconsistent rebuilds (arch drift), dirty cache/layers, stale volumes/networks,
           and race conditions with Mongo/Tor health before lucid_api starts.
    Target platform: linux/arm64 (Pi-compatible images built on Windows)
#>

# Fail fast and show useful errors
$ErrorActionPreference = 'Stop'

# --- CONFIG -------------------------------------------------------------------

# Compose file (dev stack)
$COMPOSE = '06-orchestration-runtime\compose\lucid-dev.yaml'

# Profile to use
$PROFILE = 'dev'

# Default services to bring up (will wait on health for tor-proxy & lucid_mongo if present)
$SERVICES = @()  # empty = all services in compose

# Toggle these if you want to keep caches while iterating
$CLEAN_SYSTEM = $true
$NO_CACHE     = $true

# Always build for arm64 so images run on Pi 5 later
$env:DOCKER_DEFAULT_PLATFORM = 'linux/arm64'  # enforce target arch (prevents amd64 drift)

# Dedicated builder to avoid cross-builder cache pollution
$BUILDER_NAME = 'lucid_clean'

# Health wait settings
$HEALTH_TIMEOUT_SEC = 240
$HEALTH_POLL_SEC    = 3

# --- FUNCTIONS ---------------------------------------------------------------

function Write-Info($msg)  { Write-Host "[bootstrap-dev] $msg" -ForegroundColor Cyan }
function Write-Warn($msg)  { Write-Host "[bootstrap-dev] WARN: $msg" -ForegroundColor Yellow }
function Write-Err ($msg)  { Write-Host "[bootstrap-dev] ERROR: $msg" -ForegroundColor Red }

function Assert-Tool($name, [string]$checkCmd) {
    try { & $checkCmd | Out-Null } catch { throw "Required tool '$name' not found or not working." }
}

function Ensure-Builder($builder) {
    $existing = (docker buildx ls) -join "`n"
    if ($existing -notmatch ("^\s*{0}\b" -f [regex]::Escape($builder))) {
        Write-Info "Creating Buildx builder '$builder'..."
        docker buildx create --name $builder | Out-Null
    }
    Write-Info "Using Buildx builder '$builder'..."
    docker buildx use $builder | Out-Null
}

function Compose($args) {
    # Single place to invoke docker compose with our file/profile
    $common = @('-f', $COMPOSE)
    & docker compose @common @args
}

function ComposeServiceId([string]$service) {
    $id = Compose @('ps','-q', $service) | Select-Object -First 1
    return $id
}

function Wait-Healthy([string]$service, [int]$timeoutSec, [int]$pollSec) {
    $id = ComposeServiceId $service
    if (-not $id) {
        Write-Warn "Service '$service' not found in current compose. Skipping health wait."
        return $false
    }

    $deadline = (Get-Date).AddSeconds($timeoutSec)
    do {
        # If the service has no Healthcheck, treat 'running' as success but warn.
        $inspect = docker inspect $id | ConvertFrom-Json
        $state   = $inspect[0].State
        $health  = $state.Health

        if ($null -eq $health) {
            if ($state.Status -eq 'running') {
                Write-Warn "Service '$service' has no healthcheck; container is running. Consider adding one in compose."
                return $true
            }
        } else {
            $status = $health.Status
            if ($status -eq 'healthy') {
                Write-Info "Service '$service' is healthy."
                return $true
            }
            if ($status -eq 'unhealthy') {
                # Show last lines to help debugging
                Write-Warn ("Service '{0}' reported UNHEALTHY. Recent log:" -f $service)
                docker logs --tail 25 $id | Write-Host
            }
        }

        Start-Sleep -Seconds $pollSec
    } while ((Get-Date) -lt $deadline)

    Write-Err "Timed out waiting for '$service' to become healthy."
    return $false
}

# --- PRECHECKS ----------------------------------------------------------------

Write-Info "Checking Docker prerequisites..."
Assert-Tool 'Docker'       'docker version'
Assert-Tool 'DockerCompose' 'docker compose version'
Assert-Tool 'Buildx'       'docker buildx version'

# Resolve compose file path
$COMPOSE = (Resolve-Path $COMPOSE).Path

# Enforce builder/platform
Ensure-Builder $BUILDER_NAME
Write-Info "DOCKER_DEFAULT_PLATFORM = $env:DOCKER_DEFAULT_PLATFORM"

# --- CLEAN PREV STATE ---------------------------------------------------------

Write-Info "Bringing down any existing stack (and volumes) to remove stale state..."
Compose @('down','-v')

if ($CLEAN_SYSTEM) {
    Write-Info "Pruning unused images/layers/builders (safe cleanup for clean rebuilds)..."
    docker system prune -af | Out-Null
    docker builder prune -af | Out-Null
}

# --- (RE)BUILD ---------------------------------------------------------------

$buildArgs = @('--profile', $PROFILE, 'build')
if ($NO_CACHE) { $buildArgs += '--no-cache' }

if ($SERVICES.Count -gt 0) {
    $buildArgs += $SERVICES
}

Write-Info "Building services (args: $($buildArgs -join ' '))..."
Compose $buildArgs

# --- UP ----------------------------------------------------------------------

$upArgs = @('--profile', $PROFILE, 'up','-d')
if ($SERVICES.Count -gt 0) { $upArgs += $SERVICES }

Write-Info "Starting services (args: $($upArgs -join ' '))..."
Compose $upArgs

Write-Info "Current service status:"
Compose @('ps')

# --- HEALTH GATES ------------------------------------------------------------

# Wait for critical deps first if they exist in the compose:
$deps = @('tor-proxy','lucid_mongo')

foreach ($svc in $deps) {
    try {
        [void](Wait-Healthy -service $svc -timeoutSec $HEALTH_TIMEOUT_SEC -pollSec $HEALTH_POLL_SEC)
    } catch {
        Write-Err $_.Exception.Message
        throw
    }
}

# Optionally, check lucid_api is at least running (some stacks keep API health manual)
$apiId = ComposeServiceId 'lucid_api'
if ($apiId) {
    $apiState = (docker inspect $apiId | ConvertFrom-Json)[0].State
    if ($apiState.Status -ne 'running') {
        Write-Err "lucid_api is not running (state: $($apiState.Status)). Check logs."
        docker logs --tail 100 $apiId | Write-Host
        throw "lucid_api failed to start."
    } else {
        Write-Info "lucid_api container is running."
    }
} else {
    Write-Warn "lucid_api service not found in compose (skipping API state check)."
}

# --- TAIL KEY LOGS -----------------------------------------------------------

if ($apiId) {
    Write-Info "Last 50 lines from lucid_api:"
    docker logs --tail 50 $apiId | Write-Host
}

Write-Info "Done. Stack is up with clean state and arm64 images."
Write-Info "Tip: set `$CLEAN_SYSTEM = `$false and `$NO_CACHE = `$false once your build is stable for faster cycles."
