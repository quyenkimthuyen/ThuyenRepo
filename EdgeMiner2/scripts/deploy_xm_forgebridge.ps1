[CmdletBinding()]
param(
  [string]$TerminalDataPath = "",
  [string]$InstallPath = "",
  [string]$ModelId = "",
  [double]$RiskPct = 1.0,
  [double]$PollSeconds = 2.0,
  [switch]$Attach,
  [switch]$EnableTrading,
  [switch]$RestartTerminal,
  [switch]$NoRestartTerminal,
  [bool]$StartBridgeService = $true,
  [switch]$SkipBridgeService
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SourceEa = Join-Path $RepoRoot "mt5\Experts\ForgeBridge.mq5"
$ProjectBridge = Join-Path $RepoRoot "mt5\bridge"
if (-not $ModelId) {
  $activeModelPath = Join-Path $RepoRoot "results\active_trade_model.json"
  if (Test-Path $activeModelPath) {
    $ModelId = (Get-Content $activeModelPath -Raw | ConvertFrom-Json).id
  }
  if (-not $ModelId -and $StartBridgeService -and -not $SkipBridgeService) {
    throw "No active MT5 Trade Model. Build and select a model before deployment."
  }
}

function Write-Step([string]$Message) {
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Find-XmInstallPath {
  $running = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -eq "terminal64.exe" -and
      $_.ExecutablePath -match "XM Global MT5"
    } |
    Select-Object -First 1
  if ($running -and $running.ExecutablePath) {
    return Split-Path $running.ExecutablePath
  }

  $default = "C:\Program Files\XM Global MT5"
  if (Test-Path (Join-Path $default "terminal64.exe")) {
    return $default
  }
  throw "XM Global MT5 not found. Pass -InstallPath <folder>."
}

function Find-TerminalDataPath([string]$XmInstallPath) {
  $base = Join-Path $env:APPDATA "MetaQuotes\Terminal"
  if (-not (Test-Path $base)) {
    throw "MetaQuotes Terminal data not found at $base."
  }

  $matches = Get-ChildItem $base -Directory | ForEach-Object {
    $origin = Join-Path $_.FullName "origin.txt"
    if (Test-Path $origin) {
      $originText = (Get-Content $origin -Raw).Trim()
      if ($originText -eq $XmInstallPath -or $originText -match "XM Global MT5") {
        $_
      }
    }
  } | Sort-Object LastWriteTime -Descending

  $match = $matches | Select-Object -First 1
  if (-not $match) {
    throw "XM Data Folder not found. Open XM MT5 once or pass -TerminalDataPath."
  }
  return $match.FullName
}

function Ensure-BridgeJunction([string]$DataPath) {
  $filesDir = Join-Path $DataPath "MQL5\Files"
  $link = Join-Path $filesDir "bridge"
  New-Item -ItemType Directory -Path $filesDir -Force | Out-Null
  New-Item -ItemType Directory -Path $ProjectBridge -Force | Out-Null

  if (Test-Path $link) {
    $item = Get-Item $link -Force
    if (-not $item.LinkType) {
      throw "$link exists but is not a junction. Refusing to delete existing data."
    }
    $targets = @($item.Target) | ForEach-Object { [string]$_ }
    if ($targets -notcontains $ProjectBridge) {
      throw "$link targets '$($targets -join ", ")', expected '$ProjectBridge'."
    }
    return $link
  }

  New-Item -ItemType Junction -Path $link -Target $ProjectBridge | Out-Null
  return $link
}

function Compile-Ea([string]$DataPath, [string]$XmInstallPath) {
  if (-not (Test-Path $SourceEa)) {
    throw "EA source not found: $SourceEa"
  }

  $eaDir = Join-Path $DataPath "MQL5\Experts\EdgeMiner2"
  New-Item -ItemType Directory -Path $eaDir -Force | Out-Null
  $targetMq5 = Join-Path $eaDir "ForgeBridge.mq5"
  $targetEx5 = Join-Path $eaDir "ForgeBridge.ex5"
  $compileLog = Join-Path $eaDir "ForgeBridge_compile.log"
  Copy-Item $SourceEa $targetMq5 -Force

  $editor = Join-Path $XmInstallPath "metaeditor64.exe"
  if (-not (Test-Path $editor)) {
    throw "MetaEditor not found: $editor"
  }

  Remove-Item $compileLog -Force -ErrorAction SilentlyContinue
  $proc = Start-Process -FilePath $editor `
    -ArgumentList "/compile:$targetMq5", "/log:$compileLog" `
    -PassThru -Wait

  $logText = if (Test-Path $compileLog) {
    Get-Content $compileLog -Raw -Encoding Unicode
  } else {
    ""
  }
  if ($logText -notmatch "Result:\s+0 errors,\s+0 warnings" -or -not (Test-Path $targetEx5)) {
    Write-Host $logText
    throw "ForgeBridge compile failed (MetaEditor exit=$($proc.ExitCode))."
  }

  return @{
    Source = $targetMq5
    Binary = $targetEx5
    Log = $compileLog
  }
}

function Get-ForgeBridgeCharts([string]$DataPath) {
  $chartsRoot = Join-Path $DataPath "MQL5\Profiles\Charts"
  if (-not (Test-Path $chartsRoot)) {
    return @()
  }
  return @(Get-ChildItem $chartsRoot -Filter "*.chr" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { (Get-Content $_.FullName -Raw) -match "name=ForgeBridge" })
}

function Stop-XmTerminal([string]$XmInstallPath) {
  $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -eq "terminal64.exe" -and
      $_.ExecutablePath -eq (Join-Path $XmInstallPath "terminal64.exe")
    }
  foreach ($row in $procs) {
    $proc = Get-Process -Id $row.ProcessId -ErrorAction SilentlyContinue
    if ($proc) {
      $null = $proc.CloseMainWindow()
      if (-not $proc.WaitForExit(15000)) {
        Stop-Process -Id $proc.Id -Force
      }
    }
  }
}

function Attach-ForgeBridge(
  [string]$DataPath,
  [string]$XmInstallPath,
  [bool]$TradingEnabled
) {
  Stop-XmTerminal $XmInstallPath

  $chartsRoot = Join-Path $DataPath "MQL5\Profiles\Charts"
  $allEurusdCharts = Get-ChildItem $chartsRoot -Filter "*.chr" -Recurse |
    Where-Object {
      $text = Get-Content $_.FullName -Raw
      $text -match "(?m)^symbol=EURUSD\s*$"
    }
  $charts = $allEurusdCharts |
    Where-Object {
      $text = Get-Content $_.FullName -Raw
      $text -match "(?m)^period_type=0\s*$" -and
      $text -match "(?m)^period_size=15\s*$"
    }
  if (-not $charts) {
    $charts = $allEurusdCharts
  }
  $target = $charts |
    Where-Object { (Get-Content $_.FullName -Raw) -match "name=(ForexForgeEA|ForgeBridge)" } |
    Select-Object -First 1
  if (-not $target) {
    $target = $charts | Select-Object -First 1
  }
  if (-not $target) {
    throw "EURUSD M15 chart not found in the MT5 profile."
  }

  $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
  Copy-Item $target.FullName "$($target.FullName).backup_$timestamp" -Force
  $mode = if ($TradingEnabled) { 1 } else { 0 }
  $block = @"
<expert>
name=ForgeBridge
path=Experts\EdgeMiner2\ForgeBridge.ex5
expertmode=$mode
<inputs>
InpMode=0
InpBridgeSubdir=bridge
InpDecisionWaitMs=8000
InpPollMs=500
InpChartBars=1344
InpHeartbeatMs=2000
InpHistoryChunk=750
InpRiskPct=$RiskPct
InpMagic=20260724
InpSlipPoints=30
InpMaxHoldBars=36
</inputs>
</expert>
"@

  $text = Get-Content $target.FullName -Raw
  $text = $text -replace "(?m)^period_type=\d+\s*$", "period_type=0"
  $text = $text -replace "(?m)^period_size=\d+\s*$", "period_size=15"
  if ($text -match "(?s)<expert>.*?</expert>") {
    $text = [regex]::Replace($text, "(?s)<expert>.*?</expert>", $block, 1)
  } else {
    $text = $text -replace "<window>", ($block + "`r`n<window>")
  }
  Set-Content -Path $target.FullName -Value $text -Encoding Unicode

  Start-Process -FilePath (Join-Path $XmInstallPath "terminal64.exe")
  Start-Sleep -Seconds 8
  return $target.FullName
}

function Restart-BridgeService {
  $pidFile = Join-Path $RepoRoot "results\mt5_bridge_service.pid"
  $configFile = Join-Path $RepoRoot "results\mt5_bridge_config.json"
  # Prevent the Streamlit watchdog from racing this controlled restart.
  if (Test-Path $configFile) {
    try {
      $bridgeConfig = Get-Content $configFile -Raw | ConvertFrom-Json
      $bridgeConfig.enabled = $false
      $bridgeConfig | ConvertTo-Json -Depth 8 | Set-Content $configFile -Encoding utf8
    } catch {
      Write-Warning "Could not pause Bridge watchdog: $($_.Exception.Message)"
    }
  }
  # A stale PID file can leave an older service writing to the same bridge.
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "mt5_bridge_service\.py" } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
  Start-Sleep -Milliseconds 500
  if (Test-Path $pidFile) {
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
  }

  $python = (Get-Command python -ErrorAction Stop).Source
  $pythonw = Join-Path (Split-Path $python) "pythonw.exe"
  if (-not (Test-Path $pythonw)) {
    $pythonw = $python
  }
  $commandLine = (
    "`"$pythonw`" scripts/mt5_bridge_service.py " +
    "--model-id `"$ModelId`" --risk-pct $RiskPct --poll $PollSeconds " +
    "--bridge-dir `"$ProjectBridge`""
  )
  $created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create `
    -Arguments @{ CommandLine = $commandLine; CurrentDirectory = $RepoRoot }
  if ($created.ReturnValue -ne 0) {
    throw "Cannot create Bridge service (Win32 return=$($created.ReturnValue))."
  }

  Start-Sleep -Seconds 6
  if (-not (Test-Path $pidFile)) {
    throw "Bridge service did not create a PID file. Check results\mt5_bridge_service.log."
  }
  $newPid = [int](Get-Content $pidFile -Raw)
  if (-not (Get-Process -Id $newPid -ErrorAction SilentlyContinue)) {
    throw "Bridge service PID $newPid is not running."
  }
  return $newPid
}

Write-Step "Locate XM Global MT5"
if (-not $InstallPath) {
  $InstallPath = Find-XmInstallPath
}
if (-not $TerminalDataPath) {
  $TerminalDataPath = Find-TerminalDataPath $InstallPath
}
Write-Host "Install : $InstallPath"
Write-Host "Data    : $TerminalDataPath"

Write-Step "Link MQL5 Files to app"
$bridgeLink = Ensure-BridgeJunction $TerminalDataPath
Write-Host "Bridge  : $bridgeLink -> $ProjectBridge"

Write-Step "Copy and compile ForgeBridge"
$compiled = Compile-Ea $TerminalDataPath $InstallPath
Write-Host "EX5     : $($compiled.Binary)"

$attached = Get-ForgeBridgeCharts $TerminalDataPath
if ($Attach) {
  Write-Step "Attach ForgeBridge to EURUSD M15"
  $chart = Attach-ForgeBridge $TerminalDataPath $InstallPath $EnableTrading.IsPresent
  Write-Host "Chart   : $chart"
  Write-Host "Trading : $($EnableTrading.IsPresent)"
} elseif ($attached.Count -gt 0) {
  Write-Host "Attached: $($attached[0].FullName)"
} else {
  Write-Warning "EA deployed but not attached. Run with -Attach (and -EnableTrading to allow orders)."
}

if (-not $NoRestartTerminal -and -not $Attach) {
  Write-Step "Restart XM MT5"
  Stop-XmTerminal $InstallPath
  Start-Process -FilePath (Join-Path $InstallPath "terminal64.exe")
  Start-Sleep -Seconds 8
}

if ($StartBridgeService -and -not $SkipBridgeService) {
  Write-Step "Restart MT5 Bridge service"
  $servicePid = Restart-BridgeService
  Write-Host "Service : PID $servicePid"
}

Write-Step "Done"
Write-Host "Next update command:"
Write-Host "powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`""
