<#
.SYNOPSIS
  Sanity check containers: running state, health, networks (incl. lucid_net), and published ports.

.USAGE
  # A) Explicit names (recommended)
  .\sanity_containers.ps1 -Names tor-proxy,lucid_api_gateway,tunnel

  # B) By compose project (uses label com.docker.compose.project)
  .\sanity_containers.ps1 -Project lucid-dev

  # C) By name patterns (regex OR across patterns)
  .\sanity_containers.ps1 -Patterns '^tor','gateway','tunnel'

  # Add host ports to test (e.g., 8081, 27019, 8084 when ready)
  .\sanity_containers.ps1 -Names tor-proxy,lucid_api_gateway,tunnel -Ports 8081,27019
#>

param(
  [string[]]$Names,
  [string]$Project,
  [string[]]$Patterns,
  [string]$Net = 'lucid_net',
  [int[]]$Ports = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Docker CLI not found."
}

function Get-AllNames {
  docker ps -a --format '{{.Names}}'
}

function Get-ByProject([string]$proj) {
  docker ps -a --filter "label=com.docker.compose.project=$proj" --format '{{.Names}}'
}

function Filter-ByPatterns([string[]]$all, [string[]]$pats) {
  $rx = ($pats | ForEach-Object { "(?:$_)" }) -join "|"
  if (-not $rx) { return @() }
  return $all | Where-Object { $_ -match $rx }
}

# Resolve target container list
$targets = @()
if ($Names -and $Names.Count) {
  $targets = $Names
} elseif ($Project) {
  $targets = Get-ByProject $Project
} elseif ($Patterns -and $Patterns.Count) {
  $targets = Filter-ByPatterns (Get-AllNames) $Patterns
} else {
  Write-Host "No -Names/-Project/-Patterns given; reporting all RUNNING containers." -ForegroundColor Yellow
  $targets = docker ps --format '{{.Names}}'
}

if (-not $targets -or $targets.Count -eq 0) {
  Write-Host "No containers matched." -ForegroundColor Yellow
  exit 0
}

Write-Host "`n[1/4] Status" -ForegroundColor Cyan
foreach ($n in $targets) {
  if (-not (docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $n })) {
    Write-Host "Name=$n  (not found)" -ForegroundColor DarkGray
    continue
  }
  docker ps -a --filter "name=^/$n$" --format '{{.Names}}  {{.Status}}  {{.Ports}}'
}

Write-Host "`n[2/4] Health & uptime" -ForegroundColor Cyan
foreach ($n in $targets) {
  if (docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $n }) {
    docker inspect $n --format "Name={{.Name}}  State={{.State.Status}}  Health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}  UpSince={{.State.StartedAt}}"
  }
}

Write-Host "`n[3/4] Networks (expect '$Net' present if attached)" -ForegroundColor Cyan
foreach ($n in $targets) {
  if (docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $n }) {
    $nets = docker inspect $n --format '{{range $k,$v := .NetworkSettings.Networks}}{{printf "%s " $k}}{{end}}'
    "{0}: {1}" -f $n, ($nets -replace '\s+$','') | Write-Host
  }
}

if ($Ports.Count -gt 0) {
  Write-Host "`n[4/4] Host TCP port checks" -ForegroundColor Cyan
  foreach ($p in $Ports) {
    $r = Test-NetConnection 127.0.0.1 -Port $p
    "{0}: TcpTestSucceeded={1}" -f $p, $r.TcpTestSucceeded | Write-Host
  }
} else {
  Write-Host "`n[4/4] Host TCP port checks: (skipped — pass -Ports 8081,27019,... to test)" -ForegroundColor DarkGray
}

Write-Host "`nDone." -ForegroundColor Green
