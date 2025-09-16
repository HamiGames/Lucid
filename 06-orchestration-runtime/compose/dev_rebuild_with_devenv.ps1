# Requires: Windows PowerShell 5.1+ or PowerShell 7+
# Purpose : Install dev_env first, then clean rebuild & up the dev stack

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Repo + compose + network (adjust only if your path differs)
$REPO = 'C:\Users\surba\Desktop\personal\THE_FUCKER\lucid_2'
$C    = '06-orchestration-runtime\compose\lucid-dev.yaml'
$ENVF = '06-orchestration-runtime\compose\.env'
$NET  = 'lucid-dev_lucid_net'

Set-Location $REPO

# --- CRITICAL: builder + platform (never skip)
if (-not (docker buildx ls | Select-String -Quiet '(^\*?\s*lucid_clean\b)')) {
  docker buildx create --name lucid_clean --use | Out-Null
} else {
  docker buildx use lucid_clean
}
$env:LUCID_PLATFORM='linux/amd64'
$env:DOCKER_DEFAULT_PLATFORM='linux/amd64'
$env:DOCKER_BUILDKIT='1'

# --- DEV ENV (install before building)
# Host venv for dev tooling (formatters, linters, prebuild scripts). Safe even if app runs in Docker.
$py = (Get-Command python -ErrorAction SilentlyContinue)?.Path
if (-not $py) { Write-Host "[warn] Python not found on host; skipping host venv install" }
else {
  if (-not (Test-Path ".venv")) { python -m venv .venv }
  & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip wheel setuptools
  $apiRootA = Join-Path $REPO '03-api-gateway\api'
  $apiRootB = Join-Path $REPO '03-api-gateway\api\app'
  $req = @()
  if (Test-Path (Join-Path $apiRootA 'requirements.txt')) { $req += (Join-Path $apiRootA 'requirements.txt') }
  if (Test-Path (Join-Path $apiRootB 'requirements.txt')) { $req += (Join-Path $apiRootB 'requirements.txt') }
  if ($req.Count -gt 0) {
    & ".\.venv\Scripts\python.exe" -m pip install -r $req[0]
  } else {
    & ".\.venv\Scripts\python.exe" -m pip install "uvicorn[standard]" fastapi "motor>=3" "pymongo>=4" pydantic
  }
  Write-Host "[ok] dev_env ready in .venv"
}

# --- Ensure .env keys exist (idempotent)
if (-not (Test-Path $ENVF)) { New-Item -ItemType File -Path $ENVF | Out-Null }
if (-not (Select-String -Path $ENVF -Pattern '^LUCID_ENV=' -Quiet)) {
  Add-Content $ENVF 'LUCID_ENV=dev'
}
if (-not (Select-String -Path $ENVF -Pattern '^MONGO_URL=' -Quiet)) {
  Add-Content $ENVF 'MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false'
}

# --- Network/volumes (PowerShell-safe; no ||)
if (-not (docker network ls --format '{{.Name}}' | Select-String -Quiet "^$NET$")) {
  docker network create $NET | Out-Null
}
cmd /c "docker volume inspect lucid-dev_onion_state >NUL 2>&1" ; if ($LASTEXITCODE -ne 0) { docker volume create lucid-dev_onion_state | Out-Null }
cmd /c "docker volume inspect lucid-dev_tor_data    >NUL 2>&1" ; if ($LASTEXITCODE -ne 0) { docker volume create lucid-dev_tor_data    | Out-Null }

# --- Clean down (remove orphans)
docker compose -f $C --env-file $ENVF --profile dev down --remove-orphans

# --- Build API image from the actual Dockerfile (so we don't get python:3.12-slim again)
# Auto-detect the Dockerfile under 03-api-gateway/**/api/**
$df = Get-ChildItem -Path '03-api-gateway' -Recurse -File -Include 'Dockerfile','Dockerfile.*' |
      Where-Object { $_.FullName -match '\\api(\\|$)' } |
      Sort-Object FullName | Select-Object -First 1
if (-not $df) { throw "No API Dockerfile found under 03-api-gateway\** (expected e.g. 03-api-gateway\api\Dockerfile)" }
$ctx = $df.Directory.FullName
Write-Host "[build] API Dockerfile: $($df.FullName)"
docker buildx build --platform linux/amd64 -t lucid/api:dev -f $df.FullName $ctx --load

# --- Prebuild tor/tunnel-tools (optional but keeps compose build quiet)
if (Test-Path '02-network-security\tor\Dockerfile') {
  docker buildx build --platform linux/amd64 -t lucid/tor:dev .\02-network-security\tor --load
}
if (Test-Path '02-network-security\tunnels\Dockerfile') {
  docker buildx build --platform linux/amd64 -t lucid-dev-tunnel-tools .\02-network-security\tunnels --load
}

# --- Override: pin API to the image we just built + run uvicorn; ensure Mongo healthy first
$OVR = Join-Path $env:TEMP 'lucid-override.yml'
@'
services:
  lucid_mongo:
    healthcheck:
      test: ["CMD", "mongosh", "--quiet", "--eval", "db.adminCommand({ ping: 1 }).ok"]
      interval: 10s
      timeout: 3s
      retries: 15
      start_period: 5s

  lucid_api:
    image: lucid/api:dev
    environment:
      MONGO_URL: "mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false"
    depends_on:
      lucid_mongo:
        condition: service_healthy
    working_dir: /app
    command: ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8081"]
'@ | Set-Content -Encoding UTF8 $OVR

# --- Bring stack up
docker compose -f $C -f $OVR --env-file $ENVF --profile dev up -d --build

# --- Health gates
# Tor must be healthy
$deadline = (Get-Date).AddMinutes(2)
do {
  $t = docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' lucid_tor 2>$null
  if ($t -eq 'healthy') { break }
  Start-Sleep 2
} while ((Get-Date) -lt $deadline)
if ($t -ne 'healthy') { docker logs --tail=200 lucid_tor; throw 'tor-proxy not healthy' }

# API must be running
$deadline = (Get-Date).AddMinutes(2)
do {
  $a = docker inspect -f '{{.State.Status}}' lucid_api 2>$null
  if ($a -eq 'running') { break }
  Start-Sleep 2
} while ((Get-Date) -lt $deadline)
if ($a -ne 'running') {
  docker inspect --format '{{.Config.Image}} | Entrypoint={{json .Config.Entrypoint}} Cmd={{json .Config.Cmd}}' lucid_api
  docker logs --tail=200 lucid_api
  throw 'lucid_api did not reach running'
}

# --- DNS + health from within the project network
docker run --rm --network $NET busybox nslookup lucid_api
docker run --rm --network $NET busybox nc -zv lucid_api 8081
docker run --rm --network $NET curlimages/curl -fsS "http://lucid_api:8081/health"

Write-Host "`n[done] dev_env installed; clean rebuild completed; API answering /health"
