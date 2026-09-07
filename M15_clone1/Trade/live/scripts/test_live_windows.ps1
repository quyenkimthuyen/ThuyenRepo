# Windows Live-mode E2E runner.
#
#   .\live\scripts\test_live_windows.ps1
#   .\live\scripts\test_live_windows.ps1 -WithDeploy
#   .\live\scripts\test_live_windows.ps1 -WithBridgeOnce
#   .\live\scripts\test_live_windows.ps1 -WithDeploy -WithBridgeOnce
#
[CmdletBinding()]
param(
  [switch]$WithDeploy,
  [switch]$WithBridgeOnce,
  [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$LiveRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Script = Join-Path $LiveRoot "scripts\test_live_windows.py"

if (-not (Test-Path $Script)) {
  throw "Missing test script: $Script"
}

if (-not $Python) {
  $Python = (Get-Command python -ErrorAction Stop).Source
}

$argsList = @($Script)
if ($WithDeploy) { $argsList += "--with-deploy" }
if ($WithBridgeOnce) { $argsList += "--with-bridge-once" }

Write-Host "==> Live Windows E2E"
Write-Host "Python: $Python"
Write-Host "Cwd:    $LiveRoot"
Write-Host ""

Push-Location $LiveRoot
try {
  & $Python @argsList
  exit $LASTEXITCODE
}
finally {
  Pop-Location
}
