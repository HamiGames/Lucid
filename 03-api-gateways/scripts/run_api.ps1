<#
.SYNOPSIS
  Activate the venv and run the API on 0.0.0.0:8081 with correct env.

.DESCRIPTION
  - Resolves paths using $PSScriptRoot → ..\api (matches tree.clean.txt).
  - Sets MONGO_URI (default localhost:27019) + sane LOG_LEVEL.
  - Starts uvicorn with debug logs.
  - No docker down. No killing other processes.

.NOTES
  Repo path anchor (from tree.clean.txt):
    +---03-api-gateway
        +---api
            +---app
                |   main.py
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Locate api folder from this script's directory
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApiDir     = Resolve-Path (Join-Path $ScriptRoot '..\api')
$VenvDir    = Join-Path $ApiDir '.venv'
$MainPy     = Join-Path $ApiDir 'app\main.py'

if (!(Test-Path $MainPy)) {
  Write-Error "main.py not found at $MainPy (check your checkout matches tree)."
}

# --- ENV (edit if your Mongo port differs) ---
if (-not $env:MONGO_URI) {
  # Use 27019 per your note that 27019 is free.
  $env:MONGO_URI = 'mongodb://lucid:lucid@127.0.0.1:27019/lucid?authSource=admin&retryWrites=false&directConnection=true'
}
if (-not $env:LOG_LEVEL) { $env:LOG_LEVEL = 'DEBUG' }

# Ensure venv exists/activate
$Activate = Join-Path $VenvDir 'Scripts\Activate.ps1'
if (!(Test-Path $Activate)) {
  Write-Error "Virtual env not found. Expected: $Activate"
}
& $Activate

# Echo effective config
Write-Host "API DIR     : $ApiDir"
Write-Host "VENV        : $VenvDir"
Write-Host "MONGO_URI   : $env:MONGO_URI"
Write-Host "LOG_LEVEL   : $env:LOG_LEVEL"
Write-Host "HOST:PORT   : 0.0.0.0:8081"
Write-Host ""

# cd into api dir so 'app.main:app' resolves
Set-Location $ApiDir

# Run uvicorn (stay on port 8081, as you requested)
python -c "import os; print('Python:', os.sys.version)"
$env:PYTHONUNBUFFERED = '1'
uvicorn app.main:app --host 0.0.0.0 --port 8081 --log-level debug
