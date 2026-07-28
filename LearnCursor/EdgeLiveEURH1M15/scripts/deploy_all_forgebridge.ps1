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
foreach ($job in $Jobs) {
  $i++
  $isLast = ($i -eq $Jobs.Count)
  Write-Host ""
  Write-Host ("==== [{0}/{1}] {2} {3} ====" -f $i, $Jobs.Count, $job.Timeframe, $job.Mode) `
    -ForegroundColor Yellow

  $args = @{
    Timeframe         = $job.Timeframe
    Mode              = $job.Mode
    RiskPct           = $RiskPct
    PollSeconds       = $PollSeconds
    SkipBridgeService = $true
  }
  if ($TerminalDataPath) { $args.TerminalDataPath = $TerminalDataPath }
  if ($InstallPath) { $args.InstallPath = $InstallPath }

  if ($Attach -and -not $CompileOnly) {
    $args.Attach = $true
    if ($EnableTrading -and $job.Mode -eq "Live") {
      $args.EnableTrading = $true
    }
  } else {
    # Avoid restarting MT5 4 times when only compiling
    if (-not $isLast) {
      $args.NoRestartTerminal = $true
    }
  }

  & $DeployOne @args
  if ($LASTEXITCODE -ne 0) {
    throw ("Deploy failed for {0} {1} (exit {2})" -f $job.Timeframe, $job.Mode, $LASTEXITCODE)
  }
}

Write-Host ""
Write-Host "==> All 4 EAs deployed" -ForegroundColor Green
Write-Host "EAs: ForgeBridgeM15 · ForgeBridgeM15Sim · ForgeBridgeH1 · ForgeBridgeH1Sim"
Write-Host "Next: start Live/Sim workers from MT5 Bridge (per TF)."
