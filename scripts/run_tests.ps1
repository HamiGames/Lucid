# Path: scripts/run_tests.ps1
# Test execution script

param(
    [string]$TestPath = "tests/",
    [switch]$Coverage = $true,
    [switch]$Verbose = $false
)

$cmd = "python -m pytest $TestPath"
if ($Coverage) { $cmd += " --cov=. --cov-report=html" }
if ($Verbose) { $cmd += " -v" }

Write-Host "Running tests: $cmd" -ForegroundColor Green
Invoke-Expression $cmd
