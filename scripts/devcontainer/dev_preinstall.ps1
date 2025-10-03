param(
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
  [string]$ComposeFile = ".devcontainer\docker-compose.dev.yml",
  [string]$ProjectName = "lucid-dev",
  # Default to Pi target; respects existing env override
  [string]$Platform = ($(if ($env:LUCID_PLATFORM -and $env:LUCID_PLATFORM.Trim()) {$env:LUCID_PLATFORM} else {"linux/arm64"}))
)

$ErrorActionPreference = 'Stop'
Set-Location $ProjectRoot

Write-Host "== dev_preinstall =="
Write-Host "Root: $ProjectRoot"
Write-Host "Compose: $ComposeFile"
Write-Host "Project: $ProjectName"
Write-Host "Platform: $Platform"

# --- Platform/env -------------------------------------------------------------
$env:DOCKER_DEFAULT_PLATFORM = $Platform
$env:LUCID_PLATFORM          = $Platform

# --- Docker buildx (container builder) ---------------------------------------
if (-not (docker buildx ls | Select-String -Quiet '^\s*lucid_clean\b')) {
  docker buildx create --name lucid_clean --driver docker-container --use | Out-Null
} else {
  docker buildx use lucid_clean | Out-Null
}
docker buildx inspect --bootstrap | Out-Null

# --- Compose sanity -----------------------------------------------------------
if (-not (Test-Path $ComposeFile)) { throw "Compose file not found: $ComposeFile" }
docker compose version      | Out-Null
docker compose -f $ComposeFile config > $null

# --- Tooling: yq.exe in /tools -----------------------------------------------
$TOOLS = Join-Path $ProjectRoot "tools"
$YQ    = Join-Path $TOOLS "yq.exe"
if (-not (Test-Path $TOOLS)) { New-Item -ItemType Directory -Force -Path $TOOLS | Out-Null }
if (-not (Test-Path $YQ)) {
  Write-Host "Downloading yq.exe ..."
  Invoke-WebRequest -UseBasicParsing `
    https://github.com/mikefarah/yq/releases/latest/download/yq_windows_amd64.exe `
    -OutFile $YQ
}
Write-Host "yq: $YQ"

# --- Network + volumes (idempotent) ------------------------------------------
$NET   = "${ProjectName}_lucid_net"
$ONION = "${ProjectName}_onion_state"

$null = docker network inspect $NET  2>$null
if ($LASTEXITCODE -ne 0) { docker network create $NET | Out-Null }

$null = docker volume  inspect $ONION 2>$null
if ($LASTEXITCODE -ne 0) { docker volume  create  $ONION | Out-Null }


# Ensure onion dir exists with open perms used by tor-proxy
docker run --rm -v ${ONION}:/mnt alpine:3.22.1 `
  sh -lc "install -d -m 0777 /mnt/lucid/onion && ls -ld /mnt/lucid /mnt/lucid/onion"

# --- Pre-pull common bases to stabilize builds --------------------------------
@(
  "alpine:3.22.1",
  "curlimages/curl:8.10.1",
  "busybox:latest",
  "mongo:7",
  "python:3.12-alpine"
) | ForEach-Object { docker pull $_ | Out-Null }

Write-Host "dev_preinstall completed for $ProjectName on $Platform"
