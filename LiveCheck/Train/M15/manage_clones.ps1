# Manage Streamlit apps + EA deploy for backtest desks EUR (E21) / GBP (G23).
#
# Usage:
#   .\manage_clones.ps1 Start
#   .\manage_clones.ps1 Stop
#   .\manage_clones.ps1 Restart
#   .\manage_clones.ps1 Status
#   .\manage_clones.ps1 Start -Apps EUR
#   .\manage_clones.ps1 Start -Apps G23
#   .\manage_clones.ps1 DeployEA
#   .\manage_clones.ps1 DeployEA -NoEnableTrading
#   .\manage_clones.ps1 DeployEA -NoAttach
#   .\manage_clones.ps1 DeployEA -Apps GBP
#   .\manage_clones.ps1 DeployEA -Mode Both -Apps E21,G23
#
# DeployEA attaches EA to charts and enables trading by default.
# Use -NoAttach for compile/link only; -NoEnableTrading to attach with trading off.

[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateSet("Start", "Stop", "Restart", "Status", "DeployEA")]
  [string]$Action = "Status",

  [Parameter(Position = 1)]
  [Alias("App")]
  [string[]]$Apps = @("E21", "G23"),

  [ValidateRange(5, 120)]
  [int]$TimeoutSeconds = 30,

  # --- DeployEA options (forwarded to each deploy_xm_forgebridge.ps1) ---
  [ValidateSet("Live", "HistoryFeed", "Both")]
  [string]$Mode = "Live",

  # DeployEA defaults to Attach (unless -NoAttach). -Attach is accepted for clarity.
  # -NoAttach = compile/link only; -NoEnableTrading = attach with trading off.
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
  E21 = @{ Folder = "EdgeMinerEURUSDM15"; Port = 8711; Aliases = @("EUR", "EURUSD", "M15E21") }
  G23 = @{ Folder = "EdgeMinerGBPUSDM15"; Port = 8731; Aliases = @("GBP", "GBPUSD", "M15G23") }
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
      $matched = $null

      foreach ($k in $Catalog.Keys) {
        $aliasHit = $false
        foreach ($a in @($Catalog[$k].Aliases)) {
          if ($norm -eq ($a.ToUpperInvariant() -replace '[^A-Z0-9]', '')) { $aliasHit = $true; break }
        }
        $folderNorm = ($Catalog[$k].Folder.ToUpperInvariant() -replace '[^A-Z0-9]', '')
        if ($norm -eq $k -or $aliasHit -or $norm -eq $folderNorm -or $norm -eq ("EDGEMINER" + $k)) {
          $matched = $k
          break
        }
      }

      # Accept EdgeMinerEURUSDM15 / EdgeMinerGBPUSDM15 by symbol substring
      if (-not $matched) {
        if ($norm -match 'EUR') { $matched = "E21" }
        elseif ($norm -match 'GBP') { $matched = "G23" }
      }

      if ($matched -and $Catalog.Contains($matched)) {
        if (-not $keys.Contains($matched)) { [void]$keys.Add($matched) }
        continue
      }
      throw "Unknown app '$token'. Use E21, G23, EUR, GBP, or All."
    }
  }
  if ($keys.Count -eq 0) {
    throw "No apps selected. Use -Apps E21,G23 (or EUR,GBP) or All."
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
  # Do not trust $LASTEXITCODE after calling a .ps1 (stale exit codes from Status etc).
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

  # DeployEA defaults to Attach (unless -NoAttach). -Attach is accepted for clarity.
  $doAttach = -not $NoAttach.IsPresent
  if ($Attach.IsPresent) { $doAttach = $true }
  if ($NoAttach.IsPresent) { $doAttach = $false }

  # DeployEA defaults to EnableTrading (unless -NoEnableTrading).
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
  Write-Host ("==== {0} ({1}) DeployEA Mode={2} Attach={3} Trading={4} NoRestart={5} ====" -f `
    $Key, $meta.Folder, $Mode, $doAttach, $doTrading, $noRestart) -ForegroundColor Cyan

  & $deploy @params
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
Write-Host ("backtest manage: {0} -> {1}" -f $Action, ($selected -join ", "))
if ($Action -in @("Start", "Restart", "DeployEA")) { Invoke-HealAfterMove }

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
