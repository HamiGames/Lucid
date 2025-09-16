<#
.SYNOPSIS
  Run the Blockchain Core API locally with proper env and venv.

.DESCRIPTION
  - Unique name to avoid repo-wide conflicts with other dev_server.ps1 scripts.
  - Works from any path; resolves the api folder via $PSScriptRoot.
  - Creates/activates a venv in 04-blockchain-core/api/.venv if missing.
  - Installs requirements on first run.
  - Defaults to Mongo on localhost:27019 (your free port) and port 8084 for this service.
  - Does NOT touch Docker or other running services.

.PARAMETERS
  -Port          HTTP port for this service (default 8084).
  -Mongo         Mongo URI (defaults to localhost:27019 with root user/pass 'lucid').
  -Network       Tron network (mainnet | shasta). Default: mainnet.
  -TrongridKey   Optional TRON-PRO-API-KEY for public nodes.

.USAGE
  .\run_blockchain_core.ps1
  .\run_blockchain_core.ps1 -Port 8085 -Network shasta -TrongridKey "YOUR_KEY"
#>

param(
  [int]$Port = 8084,
  [string]$Mongo = "mongodb://lucid:lucid@127.0.0.1:27019/lucid?authSource=admin&retryWrites=false&directConnection=true",
  [ValidateSet('mainnet','shasta')]
  [string]$Network = "mainnet",
  [string]$TrongridKey = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve service root: 04-blockchain-core/api
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServiceRoot = Resolve-Path (Join-Path $ScriptDir "..\api")

Write-Host "Service root : $ServiceRoot" -ForegroundColor Cyan

# Create/activate venv
$VenvActivate = Join-Path $ServiceRoot ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $VenvActivate)) {
  Write-Host "Creating virtual environment..." -ForegroundColor Yellow
  python -m venv (Join-Path $ServiceRoot ".venv")
  $VenvActivate = Join-Path $ServiceRoot ".venv\Scripts\Activate.ps1"
}
. $VenvActivate

# Install deps if needed
$Req = Join-Path $ServiceRoot "requirements.txt"
if (-not (Get-Command uvicorn -ErrorAction SilentlyContinue)) {
  Write-Host "Installing requirements..." -ForegroundColor Yellow
  python -m pip install --upgrade pip
  pip install -r $Req
}

# Session environment
$env:MONGO_URI        = $Mongo
$env:MONGO_DB         = "lucid"
$env:API_HOST         = "127.0.0.1"
$env:API_PORT         = "$Port"
$env:TRON_NETWORK     = $Network
if ($TrongridKey) { $env:TRONGRID_API_KEY = $TrongridKey }

# Provide a stable 32-byte urlsafe secret for key encryption if not supplied
if (-not $env:KEY_ENC_SECRET) {
  $bytes = New-Object byte[] 32; (New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes)
  $b64   = [Convert]::ToBase64String($bytes).TrimEnd("=").Replace('+','-').Replace('/','_')
  $env:KEY_ENC_SECRET = $b64
  Write-Host "KEY_ENC_SECRET not set; generated an ephemeral session key." -ForegroundColor DarkYellow
}

# Start server
Push-Location $ServiceRoot
$cmd = "uvicorn app.main:app --host $env:API_HOST --port $env:API_PORT --log-level debug --reload"
Write-Host "Starting: $cmd" -ForegroundColor Green
Invoke-Expression $cmd
Pop-Location
