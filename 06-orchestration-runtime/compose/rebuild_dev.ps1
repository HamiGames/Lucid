<# 
  Lucid — Clean, operational rebuild & up (Windows 11 console).
  - STRICT: uses buildx "lucid_clean", sets amd64, uses correct .env, binds, and network.
  - Preflight "project.check" runs FIRST; any failure stops the run.
  - No Bash operators (no ||). Idempotent.

  RUN:
    PS> Set-ExecutionPolicy -Scope Process Bypass
    PS> .\06-orchestration-runtime\compose\rebuild_dev.ps1
#>

$ErrorActionPreference = 'Stop'

# ==== SECTION 1 — REQUIRED BOOTSTRAP (DO NOT SKIP) ====
# Repo root (adjust ONLY if your path differs)
Set-Location 'C:\Users\surba\Desktop\personal\THE_FUCKER\lucid_2'

# Compose file + env
$C        = '06-orchestration-runtime\compose\lucid-dev.yaml'
$EnvFile  = '06-orchestration-runtime\compose\.env'
$NET      = 'lucid-dev_lucid_net'         # must match compose project/service network

# Force amd64 for Windows 11 host builds
$env:LUCID_PLATFORM          = 'linux/amd64'
$env:DOCKER_DEFAULT_PLATFORM = 'linux/amd64'
$env:DOCKER_BUILDKIT         = '1'

# Ensure Docker/Buildx ready; ensure/use "lucid_clean"
cmd /c "docker version" | Out-Null
cmd /c "docker buildx version" | Out-Null
cmd /c "docker buildx inspect lucid_clean >NUL 2>&1"
if ($LASTEXITCODE -ne 0) {
  cmd /c "docker buildx create --name lucid_clean --driver docker-container --bootstrap --use"
} else {
  cmd /c "docker buildx use lucid_clean"
}

# ==== SECTION 2 — PROJECT.CHECK (preflight gates) ====
function Require-Path([string]$p) {
  if (-not (Test-Path $p)) { throw "Missing path: $p" }
}
function Require-File([string]$p) {
  if (-not (Test-Path $p -PathType Leaf)) { throw "Missing file: $p" }
}
function Require-EnvKeys([string]$file, [string[]]$keys) {
  $map = @{}
  Get-Content $file | ForEach-Object {
    if ($_ -match '^\s*#') { return }
    if ($_ -match '^\s*$') { return }
    $kv = $_ -split '=', 2
    if ($kv.Count -eq 2) { $map[$kv[0].Trim()] = $kv[1].Trim() }
  }
  foreach ($k in $keys) {
    if (-not $map.ContainsKey($k) -or [string]::IsNullOrWhiteSpace($map[$k])) {
      throw ".env missing required key: $k"
    }
  }
}
function Ensure-Network([string]$name) {
  cmd /c "docker network inspect $name >NUL 2>&1"
  if ($LASTEXITCODE -ne 0) { cmd /c "docker network create $name" | Out-Null }
}
function Ensure-Volume([string]$name) {
  cmd /c "docker volume inspect $name >NUL 2>&1"
  if ($LASTEXITCODE -ne 0) { cmd /c "docker volume create $name" | Out-Null }
}
function Invoke-DC([string]$args) {
  $cmd = "docker compose -f `"$C`" --env-file `"$EnvFile`" $args"
  Write-Host "[compose] $cmd"
  cmd /c $cmd | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "compose failed: $args" }
}

# Paths that must exist based on repo layout
Require-File  $C
Require-File  $EnvFile
Require-Path '02-network-security\tor'
Require-Path '02-network-security\tunnels'
Require-Path '03-api-gateway\api'

# .env must minimally define these (extend if your project requires more)
Require-EnvKeys $EnvFile @(
  'LUCID_ENV',           # dev
  'MONGO_URL'            # mongodb://lucid:lucid@lucid_mongo:27017/?authSource=admin
)

# Validate compose graph
Invoke-DC "config >NUL"

# Ensure infra bits (names used across the project)
Ensure-Network $NET
# Common volumes used by tor/tunnels; create if missing
Ensure-Volume 'lucid-dev_onion_state'
Ensure-Volume 'lucid-dev_tor_data'

# Optional seeder: seed_env.ps1 if present (keeps “no placeholders” contract)
$SeederPs = Join-Path (Split-Path $C) 'seed_env.ps1'
if (Test-Path $SeederPs) { & $SeederPs }

# ==== SECTION 3 — BUILD & UP (clean) ====
# Pre-build tor to guarantee freshness; compose will (re)build the rest
Write-Host "[build] tor image"
cmd /c "docker buildx build --platform $env:LUCID_PLATFORM -t lucid/tor:dev .\02-network-security\tor --load" | Out-Host
if ($LASTEXITCODE -ne 0) { throw "tor build failed" }

# Temporary override to force tor-proxy use our local image (no rebuild)
$Override = New-TemporaryFile | ForEach-Object { $_.FullName }
@"
services:
  tor-proxy:
    image: lucid/tor:dev
    build: null
"@ | Set-Content -Encoding UTF8 -NoNewline $Override

# Down old stack, remove orphans; then Up (dev profile) with build
cmd /c "docker compose -f `"$C`" -f `"$Override`" --env-file `"$EnvFile`" down --remove-orphans" | Out-Null
Invoke-DC "-f `"$Override`" --profile dev up -d --build"

# ==== SECTION 4 — POST CHECKS (must pass) ====
# Show services
Invoke-DC "ps"

# Tor health (Bootstrapped 100%)
$torId = (cmd /c "docker compose -f `"$C`" ps -q tor-proxy").Trim()
if (-not $torId) { throw "tor-proxy container not found" }
Start-Sleep -Seconds 5
$deadline = (Get-Date).AddMinutes(2)
$ok = $false
while ((Get-Date) -lt $deadline) {
  $logs = (cmd /c "docker logs --since 5m $torId 2>&1")
  if ($logs -match 'Bootstrapped 100%') { $ok = $true; break }
  Start-Sleep -Seconds 3
}
if (-not $ok) { throw "Tor did not reach 'Bootstrapped 100%'. Check: docker logs $torId" }
Write-Host "[ok] Tor healthy"

# DNS sanity inside project network
cmd /c "docker run --rm --network `"$NET`" busybox nslookup lucid_api >NUL 2>&1" | Out-Null

# API health (via project network; adjust path if your health route differs)
# Uses curl image to avoid host tooling assumptions.
$apiCheck = "docker run --rm --network `"$NET`" curlimages/curl -fsS http://lucid_api:8081/health"
cmd /c $apiCheck | Out-Host
if ($LASTEXITCODE -ne 0) { throw "API /health failed over project network" }

# GATEWAY sanity (if exposed as lucid_api_gateway:8080; skip if not present)
$gwId = (cmd /c "docker compose -f `"$C`" ps -q lucid_api_gateway").Trim()
if ($gwId) {
  $gwCheck = "docker run --rm --network `"$NET`" curlimages/curl -fsS http://lucid_api_gateway:8080/health"
  cmd /c $gwCheck | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "Gateway /health failed over project network" }
}

# Cleanup override
Remove-Item -Force $Override

Write-Host "`n[done] Rebuild & Up successful. Builder=lucid_clean, Platform=$env:LUCID_PLATFORM, Compose=$C, Net=$NET"
