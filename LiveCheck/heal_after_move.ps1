# Heal absolute paths after LiveCheck is moved/copied.
# Safe to run anytime (idempotent).
#
#   .\heal_after_move.ps1
#   .\heal_after_move.ps1 -DryRun
#   .\heal_after_move.ps1 -Force
#
[CmdletBinding()]
param(
  [switch]$DryRun,
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Py = Join-Path $Root "scripts\heal_after_move.py"
if (-not (Test-Path $Py)) {
  throw "Missing $Py"
}

$argsList = @($Py)
if ($DryRun) { $argsList += "--dry-run" }
if ($Force) { $argsList += "--force" }

$python = $null
foreach ($c in @("python", "py")) {
  $cmd = Get-Command $c -ErrorAction SilentlyContinue
  if ($cmd) { $python = $cmd.Source; break }
}
if (-not $python) { throw "Python not found on PATH" }

Write-Host "Heal after move → $Root" -ForegroundColor Cyan
& $python @argsList
exit $LASTEXITCODE
