[CmdletBinding()]
param(
  [string]$TerminalDataPath = "",
  [string]$InstallPath = "",
  [string]$ModelId = "",
  [double]$RiskPct = 1.0,
  [double]$PollSeconds = 2.0,
  [ValidateSet("Live", "HistoryFeed")]
  [string]$Mode = "Live",
  [switch]$Attach,
  [switch]$EnableTrading,
  [switch]$RestartTerminal,
  [switch]$NoRestartTerminal,
  [bool]$StartBridgeService = $true,
  [switch]$SkipBridgeService
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SourceEaLive = Join-Path $RepoRoot "mt5\Experts\ForgeBridgeH1.mq5"
$SourceEaSim = Join-Path $RepoRoot "mt5\Experts\ForgeBridgeH1Sim.mq5"
$ProjectBridge = Join-Path $RepoRoot "mt5\bridge_h1"
$ProjectBridgeSim = Join-Path $RepoRoot "mt5\bridge_sim_h1"
$BridgeSubdirLive = "bridge_h1"
$BridgeSubdirSim = "bridge_sim_h1"
$EaNameLive = "ForgeBridgeH1"
$EaNameSim = "ForgeBridgeH1Sim"
$EaFolder = "EdgeMinerH1"
$EaMagicLive = 20260725
$EaMagicSim = 20260727
$IsHistoryFeed = ($Mode -eq "HistoryFeed")
$EaName = if ($IsHistoryFeed) { $EaNameSim } else { $EaNameLive }
$SourceEa = if ($IsHistoryFeed) { $SourceEaSim } else { $SourceEaLive }
$EaMagic = if ($IsHistoryFeed) { $EaMagicSim } else { $EaMagicLive }
if ($IsHistoryFeed) {
  # Simulate uses App feed control + bridge_sim cycle - do not restart live service.
  $SkipBridgeService = $true
}
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

function Ensure-NamedBridgeJunction(
  [string]$DataPath,
  [string]$SubdirName,
  [string]$ProjectTarget
) {
  $filesDir = Join-Path $DataPath "MQL5\Files"
  $link = Join-Path $filesDir $SubdirName
  New-Item -ItemType Directory -Path $filesDir -Force | Out-Null
  New-Item -ItemType Directory -Path $ProjectTarget -Force | Out-Null

  if (Test-Path $link) {
    $item = Get-Item $link -Force
    if (-not $item.LinkType) {
      throw "$link exists but is not a junction. Refusing to delete existing data."
    }
    $targets = @($item.Target) | ForEach-Object { [string]$_ }
    if ($targets -contains $ProjectTarget) {
      return $link
    }
    # Relink when pointing at another repo (e.g. M15 <-> H1 dual runtime).
    Write-Warning "Relinking $link from '$($targets -join ", ")' -> '$ProjectTarget'"
    cmd /c "rmdir `"$link`""
    if (Test-Path $link) {
      throw "Failed to remove old junction: $link"
    }
  }

  New-Item -ItemType Junction -Path $link -Target $ProjectTarget | Out-Null
  return $link
}

function Ensure-BridgeJunction([string]$DataPath) {
  return Ensure-NamedBridgeJunction $DataPath $BridgeSubdirLive $ProjectBridge
}

function Compile-OneEa(
  [string]$DataPath,
  [string]$XmInstallPath,
  [string]$Src,
  [string]$Name
) {
  if (-not (Test-Path $Src)) {
    throw "EA source not found: $Src"
  }

  $eaDir = Join-Path $DataPath "MQL5\Experts\$EaFolder"
  New-Item -ItemType Directory -Path $eaDir -Force | Out-Null
  $targetMq5 = Join-Path $eaDir "$Name.mq5"
  $targetEx5 = Join-Path $eaDir "$Name.ex5"
  $compileLog = Join-Path $eaDir "${Name}_compile.log"
  Copy-Item $Src $targetMq5 -Force

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
  } else { "" }
  if ($proc.ExitCode -ne 0 -and $logText -notmatch "0 error") {
    throw "$Name compile failed (MetaEditor exit=$($proc.ExitCode))."
  }
  if (-not (Test-Path $targetEx5)) {
    throw "Compile produced no EX5: $targetEx5"
  }
  return @{ Binary = $targetEx5; Log = $compileLog }
}

function Compile-Ea([string]$DataPath, [string]$XmInstallPath) {
  # Always compile Live + Sim so both can run side-by-side on the same MT5.
  $live = Compile-OneEa $DataPath $XmInstallPath $SourceEaLive $EaNameLive
  $sim = Compile-OneEa $DataPath $XmInstallPath $SourceEaSim $EaNameSim
  if ($IsHistoryFeed) { return $sim }
  return $live
}

function Stop-XmTerminal([string]$XmInstallPath) {
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -eq "terminal64.exe" -and
      $_.ExecutablePath -and
      $_.ExecutablePath.StartsWith($XmInstallPath, [System.StringComparison]::OrdinalIgnoreCase)
    } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
  Start-Sleep -Seconds 2
}

function Get-ForgeBridgeCharts([string]$DataPath) {
  $chartsRoot = Join-Path $DataPath "MQL5\Profiles\Charts"
  if (-not (Test-Path $chartsRoot)) { return @() }
  return @(Get-ChildItem $chartsRoot -Filter "*.chr" -Recurse |
    Where-Object { (Get-Content $_.FullName -Raw) -match "name=$EaName" })
}

function Get-EurusdH1Charts([string]$DataPath) {
  $chartsRoot = Join-Path $DataPath "MQL5\Profiles\Charts"
  $allEurusdCharts = Get-ChildItem $chartsRoot -Filter "*.chr" -Recurse |
    Where-Object {
      $text = Get-Content $_.FullName -Raw
      $text -match "(?m)^symbol=EURUSD\s*$"
    }
  $charts = $allEurusdCharts |
    Where-Object {
      $text = Get-Content $_.FullName -Raw
      (
        ($text -match "(?m)^period_type=0\s*$" -and $text -match "(?m)^period_size=60\s*$") -or
        $text -match "(?m)^period=60\s*$" -or
        $text -match "PERIOD_H1"
      )
    }
  if (-not $charts) {
    throw "EURUSD H1 chart not found (period_size=60). Open a EURUSD H1 chart before deploy — refusing to attach onto M15."
  }
  return @($charts)
}

function Get-EurusdM15Charts([string]$DataPath) {
  # Compat alias — H1 deploy prefers H1 charts.
  return Get-EurusdH1Charts $DataPath
}

function New-ForgeBridgeExpertBlock(
  [bool]$TradingEnabled,
  [int]$InpMode,
  [string]$BridgeSubdir
) {
  $mode = if ($TradingEnabled) { 1 } else { 0 }
  # Build as lines (avoid @"..."@ here-strings with <expert> - PS 5.1 can break on
  # smart-quotes / encoding and then treat < as the reserved redirect operator).
  $lines = @(
    '<expert>',
    "name=$EaName",
    "path=Experts\$EaFolder\$EaName.ex5",
    "expertmode=$mode",
    '<inputs>',
    "InpMode=$InpMode",
    "InpBridgeSubdir=$BridgeSubdir",
    'InpDecisionWaitMs=8000',
    'InpPollMs=500',
    'InpChartBars=336',
    'InpHeartbeatMs=2000',
    'InpHistoryChunk=750',
    'InpHistoryPaperFills=true',
    "InpRiskPct=$RiskPct",
    "InpMagic=$EaMagic",
    'InpSlipPoints=30',
    'InpMaxHoldBars=36',
    '</inputs>',
    '</expert>'
  )
  return ($lines -join "`r`n")
}

function Select-AttachChart(
  [string]$DataPath,
  [bool]$PreferHistoryFeed
) {
  $charts = Get-EurusdM15Charts $DataPath
  if (-not $charts -or $charts.Count -eq 0) {
    throw "EURUSD H1 chart not found in the MT5 profile."
  }

  if ($PreferHistoryFeed) {
    $alreadySim = $charts |
      Where-Object {
        $t = Get-Content $_.FullName -Raw
        $t -match "name=$EaNameSim" -and $t -match "InpBridgeSubdir=$BridgeSubdirSim"
      } | Select-Object -First 1
    if ($alreadySim) { return $alreadySim }

    $notLiveExpert = @($charts |
      Where-Object {
        $t = Get-Content $_.FullName -Raw
        -not (
          $t -match "name=$EaNameLive" -and
          $t -match "InpBridgeSubdir=$BridgeSubdirLive" -and
          $t -notmatch "InpBridgeSubdir=$BridgeSubdirSim"
        )
      })
    if ($notLiveExpert.Count -gt 0) {
      $empty = $notLiveExpert | Where-Object {
        (Get-Content $_.FullName -Raw) -notmatch "name=(ForgeBridgeM15Sim|ForgeBridgeM15|ForgeBridgeH1Sim|ForgeBridgeH1|ForgeBridge)"
      } | Select-Object -First 1
      if ($empty) { return $empty }
      return ($notLiveExpert | Select-Object -First 1)
    }
    if ($charts.Count -gt 1) {
      Write-Warning "Using second EURUSD chart for HistoryFeed to avoid overwriting Live."
      return $charts[1]
    }
    Write-Warning "Only one EURUSD chart found - HistoryFeed attach may replace Live inputs. Open a second chart for Live."
    return $charts[0]
  }

  $target = $charts |
    Where-Object { (Get-Content $_.FullName -Raw) -match "name=($EaNameLive|ForgeBridgeH1|ForgeBridge)" } |
    Select-Object -First 1
  if (-not $target) { $target = $charts | Select-Object -First 1 }
  return $target
}

function Attach-ForgeBridge(
  [string]$DataPath,
  [string]$XmInstallPath,
  [bool]$TradingEnabled,
  [int]$InpMode = 0,
  [string]$BridgeSubdir = $BridgeSubdirLive
) {
  Stop-XmTerminal $XmInstallPath

  $target = Select-AttachChart $DataPath ($InpMode -eq 2)
  $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
  Copy-Item $target.FullName "$($target.FullName).backup_$timestamp" -Force
  $block = New-ForgeBridgeExpertBlock $TradingEnabled $InpMode $BridgeSubdir

  $text = Get-Content $target.FullName -Raw
  $text = $text -replace '(?m)^period_type=\d+\s*$', 'period_type=0'
  $text = $text -replace '(?m)^period_size=\d+\s*$', 'period_size=60'
  # Patterns MUST stay single-quoted. Double quotes make PS parse < as redirection.
  $expertPattern = '(?s)<expert>.*?</expert>\s*'
  $windowTag = '<window>'
  $text = [regex]::Replace($text, $expertPattern, '')
  $text = [regex]::Replace($text, $windowTag, ($block + "`r`n" + $windowTag), 1)
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
  $escapedRepo = [regex]::Escape($RepoRoot)
  $escapedBridge = [regex]::Escape($ProjectBridge)
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.CommandLine -match "mt5_bridge_service\.py" -and
      ($_.CommandLine -match $escapedRepo -or $_.CommandLine -match $escapedBridge)
    } |
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
    "--monitor-port 8865 --bridge-dir `"$ProjectBridge`""
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
Write-Host "Mode    : $Mode"

Write-Step "Link MQL5 Files to app"
if ($IsHistoryFeed) {
  $bridgeLink = Ensure-NamedBridgeJunction $TerminalDataPath $BridgeSubdirSim $ProjectBridgeSim
  Write-Host "Bridge  : $bridgeLink -> $ProjectBridgeSim"
  try {
    $liveLink = Ensure-BridgeJunction $TerminalDataPath
    Write-Host "Live    : $liveLink -> $ProjectBridge"
  } catch {
    Write-Warning "Live bridge junction skipped: $($_.Exception.Message)"
  }
} else {
  $bridgeLink = Ensure-BridgeJunction $TerminalDataPath
  Write-Host "Bridge  : $bridgeLink -> $ProjectBridge"
}

Write-Step "Copy and compile $EaName"
$compiled = Compile-Ea $TerminalDataPath $InstallPath
Write-Host "EX5     : $($compiled.Binary)"

$attached = Get-ForgeBridgeCharts $TerminalDataPath
if ($Attach) {
  if ($IsHistoryFeed) {
    Write-Step "Attach $EaName HISTORY_FEED to EURUSD H1"
    $chart = Attach-ForgeBridge $TerminalDataPath $InstallPath $false 2 $BridgeSubdirSim
    Write-Host "Chart   : $chart"
    Write-Host "Inputs  : InpMode=2 (HISTORY_FEED), InpBridgeSubdir=$BridgeSubdirSim, paper fills"
  } else {
    Write-Step "Attach $EaName Live to EURUSD H1"
    $chart = Attach-ForgeBridge $TerminalDataPath $InstallPath $EnableTrading.IsPresent 0 $BridgeSubdirLive
    Write-Host "Chart   : $chart"
    Write-Host "Trading : $($EnableTrading.IsPresent)"
  }
} elseif ($attached.Count -gt 0) {
  Write-Host "Attached: $($attached[0].FullName)"
} else {
  Write-Warning "EA deployed but not attached. Run with -Attach (and -EnableTrading for Live)."
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
if ($IsHistoryFeed) {
  Write-Host "History Feed ready: App Simulate -> Start feed (sim_control.json)."
} else {
  Write-Host "Live ready. For Simulate: -Mode HistoryFeed -Attach"
}
Write-Host "Next update command:"
Write-Host "powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`""
