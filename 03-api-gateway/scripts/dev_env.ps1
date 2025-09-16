<#
.SYNOPSIS
  Set development env vars for the API session only (no system/global changes).

.DESCRIPTION
  - Mirrors schema expectations in app/config.py (pydantic).
  - Keeps BLOCK_* names consistent across project.

.USAGE
  . .\dev_env.ps1   (note: dot-source to set in current session)
#>

# Core API settings
$env:LOG_LEVEL        = 'DEBUG'
$env:MONGO_URI        = 'mongodb://lucid:lucid@127.0.0.1:27019/lucid?authSource=admin&retryWrites=false&directConnection=true'

# Blockchain metadata (optional; health endpoint can surface these if wired)
# Keep naming consistent across the project:
$env:BLOCK_ONION      = $env:BLOCK_ONION      ?? ''
$env:BLOCK_RPC_URL    = $env:BLOCK_RPC_URL    ?? ''

# JWT / Auth (if your app/config supports them)
$env:JWT_SECRET       = $env:JWT_SECRET       ?? 'dev-only-override-change-me'
$env:JWT_EXPIRES_IN   = $env:JWT_EXPIRES_IN   ?? '3600'

Write-Host "Dev env set for current session."
