<# Clean-LucidFromLists.ps1
Removes ONLY the containers, images, and volumes listed in:
  - containers_before.txt
  - images_before.txt
  - volumes_before.txt
Usage:
  .\Clean-LucidFromLists.ps1               # delete as listed
  .\Clean-LucidFromLists.ps1 -DryRun       # show what would be removed
  .\Clean-LucidFromLists.ps1 -IncludeVscodeVolumes  # also delete 'vscode' volume if listed
#>

[CmdletBinding()]
param(
  [string]$ContainersFile = ".\containers_before.txt",
  [string]$ImagesFile     = ".\images_before.txt",
  [string]$VolumesFile    = ".\volumes_before.txt",
  [switch]$DryRun,
  [switch]$IncludeVscodeVolumes
)

function Test-DockerUp {
  try { docker version --format '{{.Server.Version}}' | Out-Null; return $true } catch { return $false }
}

function Remove-ContainersFromFile {
  param([string]$Path)
  if (!(Test-Path $Path)) { Write-Verbose "No containers file."; return }
  $lines = Get-Content $Path | Where-Object { $_.Trim() -ne "" } | Select-Object -Skip 1  # skip header
  $toRemove = @()
  foreach ($l in $lines) {
    if ($l -match '^\s*([0-9a-f]{12,})\s+([^\s]+)') {
      $toRemove += $Matches[2]
    }
  }
  if ($toRemove.Count -eq 0) { return }

  Write-Host "Containers to remove: $($toRemove -join ', ')"
  if ($DryRun) { return }

  foreach ($name in $toRemove) {
    Write-Host " - removing container $name"
    docker rm -f $name 2>$null | Out-Null
  }
}

function Remove-ImagesFromFile {
  param([string]$Path)
  if (!(Test-Path $Path)) { Write-Verbose "No images file."; return }
  $lines = Get-Content $Path | Where-Object { $_.Trim() -ne "" } | Select-Object -Skip 1  # skip header

  $toRemoveIds = @()
  foreach ($l in $lines) {
    # Columns: REPOSITORY <spaces> TAG <spaces> IMAGE ID
    if ($l -match '^(?<repo>.+?)\s+(?<tag>\S+)\s+(?<id>(sha256:)?[0-9a-f]{12,})\s*$') {
      $toRemoveIds += $Matches['id']
    }
  }
  if ($toRemoveIds.Count -eq 0) { return }

  Write-Host "Images to remove (by ID): $($toRemoveIds -join ', ')"
  if ($DryRun) { return }

  foreach ($id in $toRemoveIds) {
    Write-Host " - removing image $id"
    docker rmi -f $id 2>$null | Out-Null
  }
}

function Remove-VolumesFromFile {
  param([string]$Path)
  if (!(Test-Path $Path)) { Write-Verbose "No volumes file."; return }
  $lines = Get-Content $Path | Where-Object { $_.Trim() -ne "" } | Select-Object -Skip 1  # skip header

  $toRemove = @()
  foreach ($l in $lines) {
    # Columns: DRIVER <spaces> VOLUME NAME
    if ($l -match '^\s*\S+\s+(?<name>\S+)\s*$') {
      $name = $Matches['name']
      if (-not $IncludeVscodeVolumes -and $name -eq 'vscode') { continue }
      $toRemove += $name
    }
  }
  if ($toRemove.Count -eq 0) { return }

  Write-Host "Volumes to remove: $($toRemove -join ', ')"
  if ($DryRun) { return }

  foreach ($v in $toRemove) {
    Write-Host " - removing volume $v"
    docker volume rm $v 2>$null | Out-Null
  }
}

if (-not (Test-DockerUp)) {
  Write-Host "Docker engine not up; attempting to start services (Desktop on Windows)…"
  try {
    Start-Service com.docker.service -ErrorAction SilentlyContinue
    wsl -d docker-desktop -u root -- true 2>$null
    wsl -d docker-desktop-data -u root -- true 2>$null
  } catch {}
}

Write-Host "== Removing containers =="
Remove-ContainersFromFile -Path $ContainersFile

Write-Host "== Removing images =="
Remove-ImagesFromFile -Path $ImagesFile

Write-Host "== Removing volumes =="
Remove-VolumesFromFile -Path $VolumesFile

if (-not $DryRun) {
  Write-Host "== Pruning dangling networks & cache =="
  docker network prune -f 2>$null | Out-Null
  docker builder prune -a -f 2>$null | Out-Null
}

Write-Host "Done."
