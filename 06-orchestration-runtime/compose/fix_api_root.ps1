<# Root fix for lucid_api:
   - Build API from the repo Dockerfile (not python:3.12-slim)
   - Use that image in compose via a one-shot override
   - Ensure only the correct Mongo is running and healthy
   - Run Uvicorn so DNS + /health work on $NET
#>

$ErrorActionPreference = 'Stop'

# ---- Repo + compose ----
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent (Split-Path -Parent $ScriptDir)   # .../lucid_2
Set-Location $RepoRoot

$C    = '06-orchestration-runtime\compose\lucid-dev.yaml'
$NET  = 'lucid-dev_lucid_net'
$ENVF = '06-orchestration-runtime\compose\.env'

if (-not (Test-Path $C))   { throw "Missing compose: $C" }
if (-not (Test-Path $ENVF)){ New-Item -ItemType File -Path $ENVF | Out-Null }

# ---- Required env + platform ----
if (-not (Select-String -Path $ENVF -Pattern '^LUCID_ENV=' -Quiet)) {
  Add-Content $ENVF 'LUCID_ENV=dev'
}
if (-not (Select-String -Path $ENVF -Pattern '^MONGO_URL=' -Quiet)) {
  Add-Content $ENVF 'MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false'
}
$env:LUCID_PLATFORM='linux/amd64'
$env:DOCKER_DEFAULT_PLATFORM='linux/amd64'
$env:DOCKER_BUILDKIT='1'

# ---- Buildx: ensure/use lucid_clean ----
if (-not (docker buildx ls | Select-String -Quiet '(^\*?\s*lucid_clean\b)')) {
  docker buildx create --name lucid_clean --use | Out-Null
} else { docker buildx use lucid_clean }

# ---- Network ensure (PowerShell-safe; no ||) ----
if (-not (docker network ls --format '{{.Name}}' | Select-String -Quiet "^$NET$")) {
  docker network create $NET | Out-Null
}

# ---- Kill rogue Mongos; keep only compose's lucid_mongo ----
$rogue = docker ps -a --format '{{.Names}}' |
         Where-Object { $_ -match '^(lucid-mongo|lucid_mongo_dev_\d+|lucid_mongo_\d+)$' }
if ($rogue) { $rogue | ForEach-Object { docker rm -f $_ } | Out-Null }

# ---- Bring up Mongo and wait healthy ----
docker compose -f $C --env-file $ENVF --profile dev up -d lucid_mongo | Out-Null
$deadline=(Get-Date).AddMinutes(2)
do {
  $hst = docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' lucid_mongo 2>$null
  if ($hst -eq 'healthy') { break }
  Start-Sleep 2
} while ((Get-Date) -lt $deadline)
if ($hst -ne 'healthy') { docker logs --tail=200 lucid_mongo; throw 'lucid_mongo not healthy' }

# ---- Ensure admin user lucid/lucid exists (idempotent) ----
function Test-Mongo {
  docker run --rm --network $NET mongo:7 mongosh --quiet `
    "mongodb://lucid:lucid@lucid_mongo:27017/?authSource=admin" `
    --eval "db.adminCommand({ping:1}).ok" 2>$null
}
if (-not (Test-Mongo)) {
  docker exec lucid_mongo mongosh --quiet --eval `
    'db.getSiblingDB("admin").createUser({user:"lucid",pwd:"lucid",roles:[{role:"root",db:"admin"}]})' | Out-Null
  Start-Sleep 1
}

# ---- Find the REAL API Dockerfile under 03-api-gateway/**/api/** ----
$df = Get-ChildItem -Path '03-api-gateway' -Recurse -File -Include 'Dockerfile','Dockerfile.*' |
      Where-Object { $_.FullName -match '\\api(\\|$)' } |
      Sort-Object FullName | Select-Object -First 1
if (-not $df) { throw "No API Dockerfile found under 03-api-gateway\** (expected e.g. 03-api-gateway\api\app\Dockerfile)" }

$ctx = $df.Directory.FullName
Write-Host "[build] API Dockerfile: $($df.FullName)"
Write-Host "[build] Context:        $ctx"

# ---- Build a proper API image (local) ----
docker buildx build --platform linux/amd64 -t lucid/api:dev -f $df.FullName $ctx --load

# ---- One-shot override: pin lucid_api to the built image + run Uvicorn ----
$OVR = Join-Path $env:TEMP 'lucid-override.yml'
@"
services:
  lucid_api:
    image: lucid/api:dev
    depends_on:
      lucid_mongo:
        condition: service_healthy
    environment:
      MONGO_URL: "mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false"
    working_dir: /app
    command: ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8081"]
"@ | Set-Content -Encoding UTF8 $OVR

# ---- Start API with override (replaces python:3.12-slim) ----
docker compose -f $C -f $OVR --env-file $ENVF --profile dev up -d lucid_api

# ---- Wait until RUNNING (not restarting) ----
$deadline=(Get-Date).AddMinutes(2)
do {
  $ast = docker inspect -f '{{.State.Status}}' lucid_api 2>$null
  if ($ast -eq 'running') { break }
  Start-Sleep 2
} while ((Get-Date) -lt $deadline)
if ($ast -ne 'running') {
  docker inspect --format '{{.Config.Image}} | Entrypoint={{json .Config.Entrypoint}} Cmd={{json .Config.Cmd}}' lucid_api
  docker logs --tail=200 lucid_api
  throw 'lucid_api did not reach running'
}

# ---- Prove image + command are correct (no more python:3.12-slim) ----
docker inspect --format '{{.Config.Image}} | Entrypoint={{json .Config.Entrypoint}} Cmd={{json .Config.Cmd}}' lucid_api

# ---- DNS + /health from inside the project network ----
docker run --rm --network $NET busybox nslookup lucid_api
docker run --rm --network $NET busybox nc -zv lucid_api 8081
docker run --rm --network $NET curlimages/curl -fsS "http://lucid_api:8081/health"
Write-Host "`n[ok] lucid_api is running the built image and answering /health"
