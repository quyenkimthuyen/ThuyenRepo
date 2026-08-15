# Manage Streamlit apps for backtestM5 desks (EUR/GBP M5).
#
#   .\manage_clones.ps1 Start
#   .\manage_clones.ps1 Stop
#   .\manage_clones.ps1 Restart
#   .\manage_clones.ps1 Status
#
[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateSet("Start", "Stop", "Restart", "Status")]
  [string]$Action = "Status",
  [Parameter(Position = 1)]
  [Alias("App")]
  [string[]]$Apps = @("E31", "G33"),
  [ValidateRange(5, 120)]
  [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

$Catalog = [ordered]@{
  E31 = @{ Folder = "EdgeMinerEURUSDM5"; Port = 8811; Aliases = @("EUR", "EURUSD", "M5E31", "M5") }
  G33 = @{ Folder = "EdgeMinerGBPUSDM5"; Port = 8831; Aliases = @("GBP", "GBPUSD", "M5G33", "M5") }
}

# Reuse resolver pattern from backtest/manage_clones.ps1 (simplified)
function Resolve-AppKeys([string[]]$Requested) {
  $keys = [System.Collections.Generic.List[string]]::new()
  foreach ($raw in $Requested) {
    foreach ($part in ($raw -split "[,\s]+" | Where-Object { $_ })) {
      $token = $part.Trim()
      if ($token -match '^(?i)all$') {
        foreach ($k in $Catalog.Keys) { if (-not $keys.Contains($k)) { [void]$keys.Add($k) } }
        continue
      }
      $norm = $token.ToUpperInvariant() -replace '[^A-Z0-9]', ''
      $matched = $null
      foreach ($k in $Catalog.Keys) {
        $aliasHit = $false
        foreach ($a in @($Catalog[$k].Aliases)) {
          if ($norm -eq ($a.ToUpperInvariant() -replace '[^A-Z0-9]', '')) { $aliasHit = $true; break }
        }
        $folderNorm = ($Catalog[$k].Folder.ToUpperInvariant() -replace '[^A-Z0-9]', '')
        if ($norm -eq $k -or $aliasHit -or $norm -eq $folderNorm) { $matched = $k; break }
      }
      if (-not $matched) {
        if ($norm -match 'EUR') { $matched = "E31" }
        elseif ($norm -match 'GBP') { $matched = "G33" }
      }
      if ($matched -and $Catalog.Contains($matched)) {
        if (-not $keys.Contains($matched)) { [void]$keys.Add($matched) }
        continue
      }
      throw "Unknown app '$token'. Use E31, G33, EUR, GBP, or All."
    }
  }
  if ($keys.Count -eq 0) { throw "No apps selected." }
  return ,$keys.ToArray()
}

function Invoke-CloneApp([string]$Key, [string]$ActionName) {
  $meta = $Catalog[$Key]
  $appRoot = Join-Path $Root $meta.Folder
  $runner = Join-Path $appRoot "scripts\run_app_windows.ps1"
  if (-not (Test-Path $runner)) { throw "Missing runner for ${Key}: $runner" }
  Write-Host ""
  Write-Host ("==== {0} ({1}) port {2} - {3} ====" -f $Key, $meta.Folder, $meta.Port, $ActionName) -ForegroundColor Cyan
  & $runner -Action $ActionName -Port $meta.Port -TimeoutSeconds $TimeoutSeconds
}

function Invoke-HealAfterMove {
  $liveCheck = (Resolve-Path (Join-Path $Root "..\..")).Path
  $heal = Join-Path $liveCheck "scripts\heal_after_move.py"
  if (-not (Test-Path $heal)) { return }
  try {
    $out = & python $heal 2>&1 | Out-String
    if ($out -match '"moved"\s*:\s*true' -or $out -match '"files_touched"\s*:\s*[1-9]') {
      Write-Host "Path heal after move applied." -ForegroundColor Yellow
    }
  } catch {
    Write-Host "Path heal skipped: $($_.Exception.Message)" -ForegroundColor DarkYellow
  }
}

$selected = Resolve-AppKeys $Apps
if ($Action -in @("Start", "Restart")) { Invoke-HealAfterMove }
foreach ($k in $selected) { Invoke-CloneApp -Key $k -ActionName $Action }
Write-Host ""
Write-Host "Done." -ForegroundColor Green

