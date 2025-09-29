<#
.SYNOPSIS
  Probe running API for OpenAPI, /health and /meta/ping (if present).

.DESCRIPTION
  - Safe, read-only probes.
  - Does not assume /meta/ping exists; reports clearly either way.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

param(
  [string]$BaseUrl = 'http://127.0.0.1:8081'
)

Write-Host "Probing $BaseUrl ..." -ForegroundColor Cyan

# 1) OpenAPI paths
try {
  $openapi = Invoke-RestMethod "$BaseUrl/openapi.json" -UseBasicParsing -TimeoutSec 3
  $paths = $openapi.paths.PSObject.Properties.Name
  Write-Host "`n-- OpenAPI paths --"
  $paths | ForEach-Object { $_ }
} catch {
  Write-Warning "openapi.json not reachable: $($_.Exception.Message)"
}

# 2) /health
try {
  $h = Invoke-RestMethod "$BaseUrl/health" -UseBasicParsing -TimeoutSec 3
  Write-Host "`n-- /health --"
  $h | Format-List | Out-String | Write-Host
} catch {
  Write-Warning "/health probe failed: $($_.Exception.Message)"
}

# 3) /meta/ping (optional)
try {
  $meta = Invoke-WebRequest "$BaseUrl/meta/ping" -UseBasicParsing -TimeoutSec 3
  Write-Host "`n-- /meta/ping --"
  "StatusCode: {0}" -f $meta.StatusCode | Write-Host
  if ($meta.Content) { $meta.Content | Write-Host }
} catch {
  Write-Host "`n-- /meta/ping --"
  Write-Host "Not available (or disabled). This can be fine if you don't expose it in OpenAPI."
}
