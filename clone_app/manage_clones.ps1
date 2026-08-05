# Manage Streamlit apps + EA deploy for EdgeMinerM15A6 / A7 / A8 under clone_app.
#
# Usage:
#   .\manage_clones.ps1 Start
#   .\manage_clones.ps1 Stop
#   .\manage_clones.ps1 Restart
#   .\manage_clones.ps1 Status
#   .\manage_clones.ps1 Start -Apps A6,A8
#   .\manage_clones.ps1 DeployEA
#   .\manage_clones.ps1 DeployEA -EnableTrading
#   .\manage_clones.ps1 DeployEA -NoAttach
#   .\manage_clones.ps1 DeployEA -EnableTrading -Apps A6
#   .\manage_clones.ps1 DeployEA -Mode Both -Apps A7,A8
#
# DeployEA attaches EA to charts by default. Use -NoAttach to only compile/link.
# Trading stays off unless -EnableTrading.

[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateSet("Start", "Stop", "Restart", "Status", "DeployEA")]
  [string]$Action = "Status",

  [Parameter(Position = 1)]
  [Alias("App")]
  [string[]]$Apps = @("A6", "A7", "A8"),

  [ValidateRange(5, 120)]
  [int]$TimeoutSeconds = 30,

  # --- DeployEA options (forwarded to each deploy_xm_forgebridge.ps1) ---
  [ValidateSet("Live", "HistoryFeed", "Both")]
  [string]$Mode = "Live",

  # DeployEA attaches by default; -NoAttach = compile/link only.
  [switch]$Attach,
  [switch]$NoAttach,
  [switch]$EnableTrading,
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
  A6 = @{ Folder = "EdgeMinerM15A6"; Port = 8561 }
  A7 = @{ Folder = "EdgeMinerM15A7"; Port = 8571 }
  A8 = @{ Folder = "EdgeMinerM15A8"; Port = 8581 }
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
      # Accept A6, a6, EdgeMinerM15A6, M15A6
      $norm = $token.ToUpperInvariant()
      if ($norm -match '^(?:EDGEMINER)?M15?(A[678])$' -or $norm -match '^(A[678])$') {
        $key = if ($Matches.Count -ge 2 -and $Matches[1]) { $Matches[1] } else { $Matches[0] }
        if ($Catalog.Contains($key)) {
          if (-not $keys.Contains($key)) { [void]$keys.Add($key) }
          continue
        }
      }
      throw "Unknown app '$token'. Use A6, A7, A8, or All."
    }
  }
  if ($keys.Count -eq 0) {
    throw "No apps selected. Use -Apps A6,A7,A8 or All."
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

  $params = @{
    Mode        = $Mode
    RiskPct     = $RiskPct
    PollSeconds = $PollSeconds
  }
  if ($ModelId) { $params.ModelId = $ModelId }
  if ($InstallPath) { $params.InstallPath = $InstallPath }
  if ($TerminalDataPath) { $params.TerminalDataPath = $TerminalDataPath }
  if ($doAttach) { $params.Attach = $true }
  if ($EnableTrading) { $params.EnableTrading = $true }
  if ($SkipBridgeService) { $params.SkipBridgeService = $true }
  if ($SuppressTerminalRestart -or $NoRestartTerminal) {
    $params.NoRestartTerminal = $true
  }

  $noRestart = $params.ContainsKey("NoRestartTerminal")
  Write-Host ""
  Write-Host ("==== {0} ({1}) DeployEA Mode={2} Attach={3} Trading={4} NoRestart={5} ====" -f `
    $Key, $meta.Folder, $Mode, $doAttach, [bool]$EnableTrading, $noRestart) -ForegroundColor Cyan

  & $deploy @params
}

$selected = Resolve-AppKeys $Apps
Write-Host ("clone_app manage: {0} -> {1}" -f $Action, ($selected -join ", "))

$failed = [System.Collections.Generic.List[string]]::new()
$index = 0
foreach ($key in $selected) {
  $index++
  try {
    if ($Action -eq "DeployEA") {
      # Multi-app: restart MT5 only after the last clone so sibling charts stay intact.
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
