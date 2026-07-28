[CmdletBinding()]
param(
  [string]$TerminalDataPath = "",
  [string]$InstallPath = "",
  [double]$RiskPct = 1.0,
  [double]$PollSeconds = 2.0,
  [switch]$Attach,
  [switch]$EnableTrading,
  [switch]$CompileOnly
)

$ErrorActionPreference = "Stop"
$DeployOne = Join-Path $PSScriptRoot "deploy_xm_forgebridge.ps1"
if (-not (Test-Path $DeployOne)) {
  throw "Missing deploy script: $DeployOne"
}

# Four concurrent runtimes: M15/H1 × Live/Sim
$Jobs = @(
  @{ Timeframe = "M15"; Mode = "Live" },
  @{ Timeframe = "M15"; Mode = "HistoryFeed" },
  @{ Timeframe = "H1"; Mode = "Live" },
  @{ Timeframe = "H1"; Mode = "HistoryFeed" }
)

Write-Host "==> Deploy ALL 4 EAs (M15/H1 · Live/Simulate)" -ForegroundColor Cyan
if ($CompileOnly) {
  Write-Host "Mode: compile + bridge junctions only (no chart attach)"
} elseif ($Attach) {
  Write-Host "Mode: compile + attach (need 2× EURUSD M15 + 2× EURUSD H1 free/matching charts)"
} else {
  Write-Host "Mode: compile + junctions; pass -Attach to bind charts"
}

$i = 0
$failed = @()
foreach ($job in $Jobs) {
  $i++
  $isLast = ($i -eq $Jobs.Count)
  Write-Host ""
  Write-Host ("==== [{0}/{1}] {2} {3} ====" -f $i, $Jobs.Count, $job.Timeframe, $job.Mode) `
    -ForegroundColor Yellow

  # Do NOT name this $args — that is a reserved automatic variable in PowerShell.
  $deployParams = @{
    Timeframe         = $job.Timeframe
    Mode              = $job.Mode
    RiskPct           = $RiskPct
    PollSeconds       = $PollSeconds
    SkipBridgeService = $true
  }
  if ($TerminalDataPath) { $deployParams.TerminalDataPath = $TerminalDataPath }
  if ($InstallPath) { $deployParams.InstallPath = $InstallPath }

  if ($Attach -and -not $CompileOnly) {
    $deployParams.Attach = $true
    if ($EnableTrading -and $job.Mode -eq "Live") {
      $deployParams.EnableTrading = $true
    }
  } else {
    # Avoid restarting MT5 4 times when only compiling
    if (-not $isLast) {
      $deployParams.NoRestartTerminal = $true
    }
  }

  try {
    # Nested .ps1 does not reliably set $LASTEXITCODE (often $null).
    # With ErrorActionPreference=Stop, a real failure throws; $? is the reliable check.
    & $DeployOne @deployParams
    if (-not $?) {
      throw ("Nested deploy returned failure for {0} {1}" -f $job.Timeframe, $job.Mode)
    }
    Write-Host ("OK {0} {1}" -f $job.Timeframe, $job.Mode) -ForegroundColor Green
  } catch {
    $msg = $_.Exception.Message
    Write-Host ("FAILED {0} {1}: {2}" -f $job.Timeframe, $job.Mode, $msg) -ForegroundColor Red
    $failed += ("{0} {1}: {2}" -f $job.Timeframe, $job.Mode, $msg)
  }
}

Write-Host ""
if ($failed.Count -gt 0) {
  Write-Host "==> Deploy finished with errors:" -ForegroundColor Red
  foreach ($f in $failed) { Write-Host "  - $f" -ForegroundColor Red }
  # Always try to leave MT5 running after a partial Deploy ALL
  try {
    $install = if ($InstallPath) { $InstallPath } else {
      (& {
        $running = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
          Where-Object { $_.Name -eq "terminal64.exe" -and $_.ExecutablePath -match "XM Global MT5" } |
          Select-Object -First 1
        if ($running) { Split-Path $running.ExecutablePath } else { "C:\Program Files\XM Global MT5" }
      })
    }
    $alive = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
      Where-Object {
        $_.Name -eq "terminal64.exe" -and
        $_.ExecutablePath -and
        $_.ExecutablePath.StartsWith($install, [System.StringComparison]::OrdinalIgnoreCase)
      }
    if (-not $alive -and (Test-Path (Join-Path $install "terminal64.exe"))) {
      Write-Warning "Restarting XM MT5 after partial deploy…"
      Start-Process -FilePath (Join-Path $install "terminal64.exe")
    }
  } catch {
    Write-Warning "Could not ensure MT5 is running: $($_.Exception.Message)"
  }
  throw ("Deploy ALL incomplete ({0}/{1} failed)." -f $failed.Count, $Jobs.Count)
}

Write-Host "==> All 4 EAs deployed" -ForegroundColor Green
Write-Host "EAs: ForgeBridgeM15 · ForgeBridgeM15Sim · ForgeBridgeH1 · ForgeBridgeH1Sim"
Write-Host "Next: start Live/Sim workers from MT5 Bridge (per TF)."
