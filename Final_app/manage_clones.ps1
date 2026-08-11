# Manage Streamlit apps + EA deploy for Final_app desks (EUR/GBP × M15/M5).
#
# Usage:
#   .\manage_clones.ps1 Start
#   .\manage_clones.ps1 Stop
#   .\manage_clones.ps1 Restart
#   .\manage_clones.ps1 Status
#   .\manage_clones.ps1 Start -Apps F1,F3
#   .\manage_clones.ps1 Start -Apps M15
#   .\manage_clones.ps1 Start -Apps EUR
#   .\manage_clones.ps1 DeployEA
#   .\manage_clones.ps1 DeployEA -Apps F3
#   .\manage_clones.ps1 DeployEA -Mode Both -Apps F1,F2,F3,F4
#   .\manage_clones.ps1 DeployEA -NoAttach
#   .\manage_clones.ps1 DeployEA -NoEnableTrading
#
# DeployEA attaches EA to charts and enables trading by default.
# Use -NoAttach for compile/link only; -NoEnableTrading to attach with trading off.
# Linux: use .\manage_clones.sh (no DeployEA).

[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateSet("Start", "Stop", "Restart", "Status", "DeployEA")]
  [string]$Action = "Status",

  [Parameter(Position = 1)]
  [Alias("App")]
  [string[]]$Apps = @("F1", "F2", "F3", "F4"),

  [ValidateRange(5, 120)]
  [int]$TimeoutSeconds = 30,

  # --- DeployEA options (forwarded to each deploy_xm_forgebridge.ps1) ---
  [ValidateSet("Live", "HistoryFeed", "Both")]
  [string]$Mode = "Live",

  [switch]$Attach,
  [switch]$NoAttach,
  [switch]$EnableTrading,
  [switch]$NoEnableTrading,
  [switch]$NoRestartTerminal,
  [switch]$SkipBridgeService,

  [string]$ModelId = "",
  [double]$RiskPct = 1.0,
  [double]$PollSeconds = 2.0,
  [string]$InstallPath = "",
  [string]$TerminalDataPath = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

$Catalog = [ordered]@{
  F1 = @{
    Folder = "EdgeMinerEURUSDM15"; Port = 8511
    Aliases = @("M15F1", "EURM15", "M15EUR", "E15")
    SymbolHint = "EURUSD"; TfHint = "M15"
  }
  F2 = @{
    Folder = "EdgeMinerGBPUSDM15"; Port = 8521
    Aliases = @("M15F2", "GBPM15", "M15GBP", "G15")
    SymbolHint = "GBPUSD"; TfHint = "M15"
  }
  F3 = @{
    Folder = "EdgeMinerEURUSDM5"; Port = 8531
    Aliases = @("M5F3", "EURM5", "M5EUR", "E5")
    SymbolHint = "EURUSD"; TfHint = "M5"
  }
  F4 = @{
    Folder = "EdgeMinerGBPUSDM5"; Port = 8541
    Aliases = @("M5F4", "GBPM5", "M5GBP", "G5")
    SymbolHint = "GBPUSD"; TfHint = "M5"
  }
}

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

      # Groups
      $group = @()
      if ($norm -eq "M15") { $group = @("F1", "F2") }
      elseif ($norm -eq "M5") { $group = @("F3", "F4") }
      elseif ($norm -eq "EUR" -or $norm -eq "EURUSD") { $group = @("F1", "F3") }
      elseif ($norm -eq "GBP" -or $norm -eq "GBPUSD") { $group = @("F2", "F4") }
      if ($group.Count -gt 0) {
        foreach ($g in $group) { if (-not $keys.Contains($g)) { [void]$keys.Add($g) } }
        continue
      }

      $matched = $null
      foreach ($k in $Catalog.Keys) {
        $aliasHit = $false
        foreach ($a in @($Catalog[$k].Aliases)) {
          if ($norm -eq ($a.ToUpperInvariant() -replace '[^A-Z0-9]', '')) { $aliasHit = $true; break }
        }
        $folderNorm = ($Catalog[$k].Folder.ToUpperInvariant() -replace '[^A-Z0-9]', '')
        if ($norm -eq $k -or $aliasHit -or $norm -eq $folderNorm) {
          $matched = $k
          break
        }
      }

      if ($matched -and $Catalog.Contains($matched)) {
        if (-not $keys.Contains($matched)) { [void]$keys.Add($matched) }
        continue
      }
      throw "Unknown app '$token'. Use F1 F2 F3 F4 | M15 M5 | EUR GBP | All."
    }
  }
  if ($keys.Count -eq 0) {
    throw "No apps selected."
  }
  return ,$keys.ToArray()
}

function Invoke-CloneApp {
  param(
    [string]$Key,
    [string]$ActionName
  )
  $meta = $Catalog[$Key]
  $appRoot = Join-Path $Root $meta.Folder
  $runner = Join-Path $appRoot "scripts\run_app_windows.ps1"
  if (-not (Test-Path $runner)) {
    throw "Missing runner for ${Key}: $runner"
  }
  Write-Host ""
  Write-Host ("==== {0} ({1}) port {2} - {3} ====" -f $Key, $meta.Folder, $meta.Port, $ActionName) -ForegroundColor Cyan
  & $runner -Action $ActionName -Port $meta.Port -TimeoutSeconds $TimeoutSeconds
}

function Invoke-CloneDeployEA {
  param(
    [string]$Key,
    [bool]$SuppressTerminalRestart
  )
  $meta = $Catalog[$Key]
  $appRoot = Join-Path $Root $meta.Folder
  $deploy = Join-Path $appRoot "scripts\deploy_xm_forgebridge.ps1"
  if (-not (Test-Path $deploy)) {
    throw "Missing deploy script for ${Key}: $deploy"
  }

  $doAttach = -not $NoAttach.IsPresent
  if ($Attach.IsPresent) { $doAttach = $true }
  if ($NoAttach.IsPresent) { $doAttach = $false }

  $doTrading = -not $NoEnableTrading.IsPresent
  if ($EnableTrading.IsPresent) { $doTrading = $true }
  if ($NoEnableTrading.IsPresent) { $doTrading = $false }

  $params = @{
    Mode        = $Mode
    RiskPct     = $RiskPct
    PollSeconds = $PollSeconds
  }
  if ($ModelId) { $params.ModelId = $ModelId }
  if ($InstallPath) { $params.InstallPath = $InstallPath }
  if ($TerminalDataPath) { $params.TerminalDataPath = $TerminalDataPath }
  if ($doAttach) { $params.Attach = $true }
  if ($doTrading) { $params.EnableTrading = $true }
  if ($SkipBridgeService) { $params.SkipBridgeService = $true }
  if ($SuppressTerminalRestart -or $NoRestartTerminal) {
    $params.NoRestartTerminal = $true
  }

  $noRestart = $params.ContainsKey("NoRestartTerminal")
  Write-Host ""
  Write-Host ("==== {0} ({1}) DeployEA Mode={2} Attach={3} Trading={4} NoRestart={5} ({6} {7}) ====" -f `
    $Key, $meta.Folder, $Mode, $doAttach, $doTrading, $noRestart, $meta.SymbolHint, $meta.TfHint) -ForegroundColor Cyan

  & $deploy @params
}

$selected = Resolve-AppKeys $Apps
Write-Host ("Final_app manage: {0} -> {1}" -f $Action, ($selected -join ", "))

$failed = [System.Collections.Generic.List[string]]::new()
$index = 0
foreach ($key in $selected) {
  $index++
  try {
    if ($Action -eq "DeployEA") {
      # Multi-app: restart MT5 only after the last desk so sibling charts stay intact.
      $suppressRestart = ($selected.Count -gt 1) -and ($index -lt $selected.Count)
      Invoke-CloneDeployEA -Key $key -SuppressTerminalRestart:$suppressRestart
    }
    else {
      Invoke-CloneApp -Key $key -ActionName $Action
    }
  }
  catch {
    Write-Host ("ERROR {0}: {1}" -f $key, $_.Exception.Message) -ForegroundColor Red
    [void]$failed.Add($key)
  }
}

Write-Host ""
if ($failed.Count -gt 0) {
  Write-Host ("Done with errors: {0}" -f ($failed -join ", ")) -ForegroundColor Yellow
  exit 1
}
Write-Host "Done." -ForegroundColor Green
