<#
.SYNOPSIS
  Start a local MongoDB 7 container on host port 27019 safely (no docker down).

.DESCRIPTION
  - Names the container: lucid_mongo_27019
  - Uses --platform linux/amd64 to avoid the ARM image mismatch warning on Windows.
  - Fails fast if 27019 is taken. Does NOT stop other containers or services.
  - Creates a named volume for persistence.

.USAGE
  ./mongo_27019.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Port        = 27019
$Container   = 'lucid_mongo_27019'
$Volume      = 'lucid_mongo_27019_data'
$MongoImage  = 'mongo:7'

# Port check
$portBusy = (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
if ($portBusy) {
  Write-Error "Host port $Port is already in use. Choose a different port or stop the owning process."
}

# Create volume if missing
$vol = docker volume ls --format '{{.Name}}' | Where-Object { $_ -eq $Volume }
if (-not $vol) {
  Write-Host "Creating volume $Volume ..."
  docker volume create $Volume | Out-Null
}

# Existing container check
$existing = docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $Container }
if ($existing) {
  $state = docker inspect -f '{{.State.Status}}' $Container
  if ($state -ne 'running') {
    Write-Host "Starting existing container $Container ..."
    docker start $Container | Out-Null
  } else {
    Write-Host "Container $Container already running on port $Port."
  }
  exit 0
}

# Run new
Write-Host "Starting $Container on port $Port ..."
docker run -d `
  --name $Container `
  --platform linux/amd64 `
  -p "${Port}:27017" `
  -e MONGO_INITDB_ROOT_USERNAME=lucid `
  -e MONGO_INITDB_ROOT_PASSWORD=lucid `
  -e MONGO_INITDB_DATABASE=lucid `
  -v "${Volume}:/data/db" `
  --restart unless-stopped `
  $MongoImage | Out-Null

Start-Sleep -Seconds 2
docker ps --filter "name=$Container"
Write-Host "Mongo ready on mongodb://lucid:lucid@127.0.0.1:${Port}/?authSource=admin"
