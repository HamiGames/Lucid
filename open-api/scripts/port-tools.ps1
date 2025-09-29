<#
.SYNOPSIS
  Safe helpers to inspect (default) and optionally stop a process bound to a TCP port.

.DESCRIPTION
  - By default, READ-ONLY: shows the owning process + path.
  - To actually stop a process, you MUST pass -Force.
  - This reduces risk of killing uvicorn or any long-running job by accident.

.EXAMPLES
  . .\port-tools.ps1; Get-Port -Port 8081
  . .\port-tools.ps1; Close-Port -Port 27019 -Force
#>

function Get-Port {
  [CmdletBinding()]
  param([Parameter(Mandatory)][int]$Port)

  $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
  if (-not $conn) { Write-Host "Port $Port is free."; return }
  $pid = $conn.OwningProcess
  try {
    $p = Get-Process -Id $pid -ErrorAction Stop
    $path = ($p.Path) ? $p.Path : '(path unavailable)'
  } catch { $p = $null; $path = '(process info unavailable)' }

  [pscustomobject]@{
    Port      = $Port
    State     = $conn.State
    PID       = $pid
    Process   = if ($p) { $p.ProcessName } else { '(unknown)' }
    Path      = $path
    LocalAddr = $conn.LocalAddress
  }
}

function Close-Port {
  [CmdletBinding(SupportsShouldProcess)]
  param(
    [Parameter(Mandatory)][int]$Port,
    [switch]$Force
  )

  $info = Get-Port -Port $Port
  if ($info -isnot [object]) { return } # port free

  if (-not $Force) {
    Write-Warning "Refusing to stop PID $($info.PID) on port $Port without -Force."
    return
  }

  Write-Host "Stopping PID $($info.PID) ($($info.Process)) on port $Port ..."
  Stop-Process -Id $info.PID -Force
  Start-Sleep -Milliseconds 300
  Write-Host "Done. Re-check:"
  Get-Port -Port $Port | Format-List | Out-String | Write-Host
}

Export-ModuleMember -Function Get-Port, Close-Port
