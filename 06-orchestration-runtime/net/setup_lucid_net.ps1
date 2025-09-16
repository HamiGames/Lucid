<#
.SYNOPSIS
  Create and manage the shared Docker network **lucid_net** used by tor-proxy and tunnel systems.

.DESCRIPTION
  - Idempotently creates a dedicated bridge network named `lucid_net`.
  - Auto-selects a free private subnet to avoid clashes with existing Docker networks.
  - Labels the network for project discovery.
  - (Optional) Connects known containers (tor-proxy, blockchain-core, gateway, mongo) if present.
  - No destructive operations (does NOT remove or recreate an existing lucid_net unless -Recreate is set).

.PARAMETERS
  -Subnet       CIDR to use (e.g., 172.28.0.0/16). If omitted, the script chooses a free subnet.
  -Gateway      IP address for the gateway inside the subnet (defaults to .1 within chosen subnet).
  -Connect      Also connect known containers if they exist (safe: only connects, never restarts).
  -Containers   Explicit container names to connect (overrides defaults).
  -Recreate     If lucid_net exists, remove and recreate (DANGEROUS – only if you really need to change IPAM).

.DEFAULTS
  Candidate subnets (first free will be used if -Subnet not given):
    172.28.0.0/16, 172.29.0.0/16, 172.30.0.0/16, 172.31.0.0/16, 10.88.0.0/16, 10.89.0.0/16

.EXAMPLES
  # Create lucid_net (auto subnet) – typical use
  .\setup_lucid_net.ps1

  # Create with explicit subnet
  .\setup_lucid_net.ps1 -Subnet 172.30.0.0/16

  # Create and connect running containers to lucid_net
  .\setup_lucid_net.ps1 -Connect

  # Force rebuild of lucid_net with a new subnet (will disconnect any attached containers!)
  .\setup_lucid_net.ps1 -Recreate -Subnet 172.31.0.0/16
#>

[CmdletBinding()]
param(
  [string]$Subnet,
  [string]$Gateway,
  [switch]$Connect,
  [string[]]$Containers,
  [switch]$Recreate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-Docker {
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI not found in PATH. Install Docker Desktop and retry."
  }
}

function Get-ExistingDockerSubnets {
  $ids = docker network ls -q
  $subnets = @()
  foreach ($id in $ids) {
    try {
      $cfgJson = docker network inspect $id --format '{{json .IPAM.Config}}'
      if ([string]::IsNullOrWhiteSpace($cfgJson)) { continue }
      $cfg = $cfgJson | ConvertFrom-Json
      foreach ($c in $cfg) {
        if ($c.Subnet) { $subnets += [string]$c.Subnet }
      }
    } catch { }
  }
  return $subnets | Sort-Object -Unique
}

function Find-FreeSubnet {
  param([string[]]$Candidates)
  $existing = Get-ExistingDockerSubnets
  foreach ($cidr in $Candidates) {
    if ($existing -notcontains $cidr) { return $cidr }
  }
  throw "No free subnet available from candidates: $($Candidates -join ', ')`nExisting: $($existing -join ', ')"
}

function Derive-Gateway {
  param([Parameter(Mandatory)][string]$Cidr)
  # expects A.B.C.D/nn -> returns A.B.C.1
  $base = $Cidr -replace '/\d+$',''
  $oct = $base.Split('.')
  if ($oct.Count -ne 4) { throw "Invalid CIDR: $Cidr" }
  return "{0}.{1}.{2}.1" -f $oct[0],$oct[1],$oct[2]
}

function New-LucidNet {
  param([string]$Cidr, [string]$Gw)
  Write-Host "Creating docker network 'lucid_net' with subnet $Cidr gateway $Gw ..." -ForegroundColor Cyan
  docker network create `
    --driver bridge `
    --subnet $Cidr `
    --gateway $Gw `
    --label "lucid.project=lucid" `
    --label "lucid.role=mesh" `
    --label "lucid.part=net" `
    lucid_net | Out-Null
  Write-Host "Created 'lucid_net'." -ForegroundColor Green
}

function Ensure-LucidNet {
  param([string]$Cidr, [string]$Gw, [switch]$ForceRecreate)
  $exists = docker network ls --format '{{.Name}}' | Where-Object { $_ -eq 'lucid_net' }
  if (-not $exists) {
    New-LucidNet -Cidr $Cidr -Gw $Gw
    return
  }

  # Inspect existing IPAM
  $cfgJson = docker network inspect lucid_net --format '{{json .IPAM.Config}}'
  $cfg = $cfgJson | ConvertFrom-Json
  $curSubnet = ($cfg | Where-Object { $_.Subnet })[0].Subnet
  $curGateway = ($cfg | Where-Object { $_.Gateway })[0].Gateway

  if ($curSubnet -eq $Cidr -and ($curGateway -eq $Gw -or [string]::IsNullOrWhiteSpace($Gw))) {
    Write-Host "Network 'lucid_net' already exists with subnet $curSubnet (gateway $curGateway). Reusing." -ForegroundColor Yellow
    return
  }

  if (-not $ForceRecreate) {
    Write-Warning "Network 'lucid_net' exists with subnet=$curSubnet gateway=$curGateway; differs from requested subnet=$Cidr gateway=$Gw."
    Write-Warning "Use -Recreate to remove and re-create (containers attached will be disconnected!)."
    return
  }

  Write-Host "Recreating 'lucid_net' to match requested IPAM..." -ForegroundColor DarkYellow
  docker network rm lucid_net | Out-Null
  New-LucidNet -Cidr $Cidr -Gw $Gw
}

function Test-ContainerExists {
  param([Parameter(Mandatory)][string]$Name)
  return [bool](docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $Name })
}

function Get-ContainerNetworks {
  param([Parameter(Mandatory)][string]$Name)
  $nets = @()
  $ids = docker inspect $Name --format '{{range .NetworkSettings.Networks}}{{println .NetworkID}}{{end}}' 2>$null
  foreach ($nid in $ids) {
    if ([string]::IsNullOrWhiteSpace($nid)) { continue }
    $n = docker network inspect --format '{{.Name}}' $nid 2>$null
    if ($n) { $nets += $n }
  }
  return $nets
}

function Connect-IfPresent {
  param([Parameter(Mandatory)][string]$Name)
  if (-not (Test-ContainerExists -Name $Name)) { return }
  $nets = Get-ContainerNetworks -Name $Name
  if ($nets -contains 'lucid_net') {
    Write-Host "Container '$Name' already attached to lucid_net." -ForegroundColor Gray
    return
  }
  Write-Host "Connecting '$Name' to lucid_net..." -ForegroundColor Cyan
  docker network connect lucid_net $Name | Out-Null
}

# --- MAIN ---

Assert-Docker

$candidates = @('172.28.0.0/16','172.29.0.0/16','172.30.0.0/16','172.31.0.0/16','10.88.0.0/16','10.89.0.0/16')

if (-not $Subnet -or [string]::IsNullOrWhiteSpace($Subnet)) {
  $Subnet = Find-FreeSubnet -Candidates $candidates
}
if (-not $Gateway -or [string]::IsNullOrWhiteSpace($Gateway)) {
  $Gateway = Derive-Gateway -Cidr $Subnet
}

Ensure-LucidNet -Cidr $Subnet -Gw $Gateway -ForceRecreate:$Recreate

if ($Connect) {
  # Known/likely container names in this project. Adjust as needed.
  # - tor-proxy service (02-network-security/tor)
  # - blockchain core (04-blockchain-core)
  # - api gateway (03-api-gateway)
  # - mongo sidecar used in local dev
  $default = @('tor-proxy','lucid_tor_proxy','lucid_blockchain_core','lucid_api_gateway','lucid_mongo_27019')
  if ($Containers -and $Containers.Count -gt 0) {
    $list = $Containers
  } else {
    $list = $default
  }
  foreach ($c in $list) { Connect-IfPresent -Name $c }
}

# Final report
Write-Host ""
Write-Host "lucid_net status:" -ForegroundColor Cyan
docker network inspect lucid_net --format 'Name={{.Name}}  Driver={{.Driver}}  Subnet={{ (index .IPAM.Config 0).Subnet }}  Gateway={{ (index .IPAM.Config 0).Gateway }}'
Write-Host "Done." -ForegroundColor Green
