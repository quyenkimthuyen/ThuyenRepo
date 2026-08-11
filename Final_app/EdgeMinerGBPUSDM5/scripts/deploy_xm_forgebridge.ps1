[CmdletBinding()]
param(
  [string]$TerminalDataPath = "",
  [string]$InstallPath = "",
  [string]$ModelId = "",
  [double]$RiskPct = 1.0,
  [double]$PollSeconds = 2.0,
  [ValidateSet("Live", "HistoryFeed", "Both")]
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
$SourceEaLive = Join-Path $RepoRoot "mt5\Experts\ForgeBridgeM5F4.mq5"
$SourceEaSim = Join-Path $RepoRoot "mt5\Experts\ForgeBridgeM5F4Sim.mq5"
$ProjectBridge = Join-Path $RepoRoot "mt5\bridge_m5f4"
$ProjectBridgeSim = Join-Path $RepoRoot "mt5\bridge_sim_m5f4"
$BridgeSubdirLive = "bridge_m5f4"
$BridgeSubdirSim = "bridge_sim_m5f4"
$EaNameLive = "ForgeBridgeM5F4"
$EaNameSim = "ForgeBridgeM5F4Sim"
$EaFolder = "EdgeMinerGBPUSDM5"
$EaMagicLive = 20261561
$EaMagicSim = 20262561
$IsBoth = ($Mode -eq "Both")
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
  # Compile ONLY the EA for the selected Mode (Live or HistoryFeed).
  return Compile-OneEa $DataPath $XmInstallPath $SourceEa $EaName
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

function Get-ActiveChartsRoot([string]$DataPath) {
  $commonIni = Join-Path $DataPath "config\common.ini"
  if (-not (Test-Path $commonIni)) {
    throw "MT5 common.ini not found: $commonIni"
  }
  $commonText = Get-Content $commonIni -Raw
  $profileMatch = [regex]::Match($commonText, '(?m)^ProfileLast=(.+?)\s*$')
  if (-not $profileMatch.Success) {
    throw "Cannot determine the active MT5 chart profile from $commonIni."
  }
  $profileName = $profileMatch.Groups[1].Value.Trim()
  if ((Split-Path $profileName -Leaf) -ne $profileName) {
    throw "Invalid active MT5 profile name: $profileName"
  }
  $chartsRoot = Join-Path $DataPath "MQL5\Profiles\Charts\$profileName"
  New-Item -ItemType Directory -Path $chartsRoot -Force | Out-Null
  return $chartsRoot
}

function Get-ForgeBridgeCharts([string]$DataPath) {
  $chartsRoot = Get-ActiveChartsRoot $DataPath
  if (-not (Test-Path $chartsRoot)) { return @() }
  return @(Get-ChildItem $chartsRoot -Filter "*.chr" -Recurse |
    Where-Object { (Get-Content $_.FullName -Raw) -match "name=$EaName" })
}

function Get-GBPUSDM15Charts([string]$DataPath) {
  $chartsRoot = Get-ActiveChartsRoot $DataPath
  $allGBPUSDCharts = Get-ChildItem $chartsRoot -Filter "*.chr" -Recurse |
    Where-Object {
      $text = Get-Content $_.FullName -Raw
      $text -match "(?m)^symbol=GBPUSD\s*$"
    }
  $charts = $allGBPUSDCharts |
    Where-Object {
      $text = Get-Content $_.FullName -Raw
      $text -match "(?m)^period_type=0\s*$" -and
      $text -match "(?m)^period_size=15\s*$"
    }
  return @($charts)
}

function New-MinimalGBPUSDChartText(
  [int]$PeriodType,
  [int]$PeriodSize
) {
  $id = [DateTime]::UtcNow.Ticks
  $lines = @(
    '<chart>',
    "id=$id",
    'symbol=GBPUSD',
    "period_type=$PeriodType",
    "period_size=$PeriodSize",
    'digits=5',
    'tick_size=0.000000',
    'scale_fix=0',
    'scale_bar=0',
    'scale=8',
    'mode=1',
    'fore=0',
    'grid=1',
    'volume=0',
    'scroll=1',
    'shift=1',
    'shift_size=20.000000',
    'ohlc=0',
    'bidline=1',
    'askline=0',
    'lastline=0',
    'days=0',
    'descriptions=0',
    'windows_total=1',
    'window_type=1',
    'background_color=0',
    'foreground_color=16777215',
    'barup_color=65280',
    'bardown_color=65280',
    'bullcandle_color=0',
    'bearcandle_color=16777215',
    'chartline_color=65280',
    'volumes_color=3329330',
    'grid_color=10061943',
    'bidline_color=10061943',
    'askline_color=255',
    'lastline_color=49152',
    'stops_color=255',
    '',
    '<window>',
    'height=100',
    '',
    '<indicator>',
    'name=Main',
    'path=',
    'apply=1',
    'show_data=1',
    'scale_inherit=0',
    'scale_line=0',
    'scale_line_percent=50',
    'scale_line_value=0.000000',
    'scale_fix_min=0',
    'scale_fix_min_val=0.000000',
    'scale_fix_max=0',
    'scale_fix_max_val=0.000000',
    '</indicator>',
    '</window>',
    '</chart>'
  )
  return ($lines -join "`r`n")
}

function Find-GBPUSDChartTemplate([string]$DataPath) {
  $chartsBase = Join-Path $DataPath "MQL5\Profiles\Charts"
  if (-not (Test-Path $chartsBase)) { return $null }
  $family = Get-ForgeFamilyPattern
  $all = @(Get-ChildItem $chartsBase -Filter "*.chr" -Recurse -ErrorAction SilentlyContinue |
    Where-Object {
      (Get-Content $_.FullName -Raw) -match "(?m)^symbol=GBPUSD\s*$"
    })
  if ($all.Count -eq 0) { return $null }
  $free = @($all | Where-Object {
    (Get-Content $_.FullName -Raw) -notmatch $family
  } | Select-Object -First 1)
  if ($free.Count -gt 0) { return $free[0] }
  return $all[0]
}

function New-GBPUSDM15Chart([string]$DataPath) {
  $chartsRoot = Get-ActiveChartsRoot $DataPath
  $family = Get-ForgeFamilyPattern
  $templates = @(Get-ChildItem $chartsRoot -Filter "*.chr" -ErrorAction SilentlyContinue |
    Where-Object {
      (Get-Content $_.FullName -Raw) -match "(?m)^symbol=GBPUSD\s*$"
    })
  # Active profile empty (e.g. Default with 0 charts) - borrow GBPUSD from any profile.
  if ($templates.Count -eq 0) {
    $borrowed = Find-GBPUSDChartTemplate $DataPath
    if ($borrowed) {
      Write-Host "No GBPUSD in active profile; using template from $($borrowed.Directory.Name)\$($borrowed.Name)"
      $templates = @($borrowed)
    }
  }

  $usedNumbers = @(Get-ChildItem $chartsRoot -Filter "chart*.chr" -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.BaseName -match '^chart(\d+)$') { [int]$Matches[1] }
  })
  [int]$nextNumber = if ($usedNumbers.Count -gt 0) {
    [int](($usedNumbers | Measure-Object -Maximum).Maximum) + 1
  } else { 1 }
  $targetPath = Join-Path $chartsRoot ("chart{0:D2}.chr" -f $nextNumber)

  if ($templates.Count -eq 0) {
    Write-Host "No GBPUSD template anywhere - creating blank GBPUSD M5 chart."
    $text = New-MinimalGBPUSDChartText 0 15
  } else {
    $template = @($templates | Where-Object {
      (Get-Content $_.FullName -Raw) -notmatch $family
    } | Select-Object -First 1)
    if ($template.Count -eq 0) {
      $template = @($templates | Select-Object -First 1)
    }
    $text = Get-Content $template[0].FullName -Raw
    $text = $text -replace '(?m)^id=\d+\s*$', ("id=" + [DateTime]::UtcNow.Ticks)
    $text = $text -replace '(?m)^period_type=\d+\s*$', 'period_type=0'
    $text = $text -replace '(?m)^period_size=\d+\s*$', 'period_size=15'
    # Match every ForgeBridge* (stock M15/H1 + clones M15B4/M15B5/...) so we never
    # copy a sibling instance's expert onto a new chart template.
    $forgeExpertPattern = '(?s)<expert>\s*name=ForgeBridge[A-Za-z0-9]*\b.*?</expert>\s*'
    $text = [regex]::Replace($text, $forgeExpertPattern, '')
  }
  Set-Content -Path $targetPath -Value $text -Encoding Unicode
  Write-Host "Created GBPUSD M5 chart in active profile: $targetPath"
  return Get-Item $targetPath
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
    'InpChartBars=1344',
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

function Get-ForgeFamilyPattern {
  return 'name=ForgeBridge[A-Za-z0-9]*\b'
}

function Select-AttachChart(
  [string]$DataPath,
  [bool]$PreferHistoryFeed
) {
  $charts = Get-GBPUSDM15Charts $DataPath
  if (-not $charts -or $charts.Count -eq 0) {
    $charts = @(New-GBPUSDM15Chart $DataPath)
  }

  $wantedName = if ($PreferHistoryFeed) { $EaNameSim } else { $EaNameLive }
  $otherName = if ($PreferHistoryFeed) { $EaNameLive } else { $EaNameSim }
  $family = Get-ForgeFamilyPattern

  # 1) Re-attach only the chart that already has THIS EA name.
  $same = @($charts | Where-Object {
    (Get-Content $_.FullName -Raw) -match ("name=" + [regex]::Escape($wantedName))
  })
  if ($same.Count -gt 0) {
    Write-Host "Attach target: existing $wantedName on $($same[0].Name)"
    return $same[0]
  }

  # 2) Prefer a chart with no ForgeBridge* EA (do not touch Live/Sim/other TF EAs).
  $free = @($charts | Where-Object {
    (Get-Content $_.FullName -Raw) -notmatch $family
  })
  if ($free.Count -gt 0) {
    Write-Host "Attach target: free GBPUSD M5 chart $($free[0].Name) for $wantedName"
    return $free[0]
  }

  # 3) All M15 charts already have a ForgeBridge* EA - create a new chart
  #    (clone template, strip experts) instead of overwriting Live <-> Sim.
  Write-Host "No free GBPUSD M5 chart for $wantedName; creating a new chart (keep $otherName intact)."
  $created = @(New-GBPUSDM15Chart $DataPath)
  if ($created.Count -eq 0) {
    throw ("Failed to create GBPUSD M5 chart for $wantedName.")
  }
  Write-Host "Attach target: new chart $($created[0].Name) for $wantedName"
  return $created[0]
}

function Write-ForgeBridgeToChart(
  [string]$DataPath,
  [bool]$TradingEnabled,
  [int]$InpMode = 0,
  [string]$BridgeSubdir = $BridgeSubdirLive,
  [string]$ExpertName,
  [int]$Magic
) {
  <#
    Patch a chart profile to attach ExpertName. Does NOT stop/start MT5 -
    caller stops once, writes Live+Sim charts, then starts once.
  #>
  $prevName = $script:EaName
  $prevMagic = $script:EaMagic
  $script:EaName = $ExpertName
  $script:EaMagic = $Magic
  try {
    $target = Select-AttachChart $DataPath ($InpMode -eq 2)
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item $target.FullName "$($target.FullName).backup_$timestamp" -Force
    $block = New-ForgeBridgeExpertBlock $TradingEnabled $InpMode $BridgeSubdir

    $text = Get-Content $target.FullName -Raw
    $text = $text -replace '(?m)^period_type=\d+\s*$', 'period_type=0'
    $text = $text -replace '(?m)^period_size=\d+\s*$', 'period_size=15'
    $forgeExpertPattern = '(?s)<expert>\s*name=ForgeBridge[A-Za-z0-9]*\b.*?</expert>\s*'
    $windowTag = '<window>'
    $text = [regex]::Replace($text, $forgeExpertPattern, '')
    if ($text -notmatch [regex]::Escape($windowTag)) {
      if ($text -notmatch '</chart>') {
        throw "Chart $($target.FullName) has neither <window> nor </chart>; cannot attach $ExpertName."
      }
      $text = $text -replace '(?m)^windows_total=0\s*$', 'windows_total=1'
      $mainWindow = @(
        '<window>',
        'height=100',
        '',
        '<indicator>',
        'name=Main',
        'path=',
        'apply=1',
        'show_data=1',
        'scale_inherit=0',
        'scale_line=0',
        'scale_line_percent=50',
        'scale_line_value=0.000000',
        'scale_fix_min=0',
        'scale_fix_min_val=0.000000',
        'scale_fix_max=0',
        'scale_fix_max_val=0.000000',
        '</indicator>',
        '</window>'
      ) -join "`r`n"
      $text = [regex]::Replace(
        $text,
        '</chart>',
        ($mainWindow + "`r`n</chart>"),
        1
      )
    }
    $text = [regex]::Replace($text, $windowTag, ($block + "`r`n" + $windowTag), 1)
    Set-Content -Path $target.FullName -Value $text -Encoding Unicode
    Write-Host "Attached $ExpertName (mode=$InpMode, subdir=$BridgeSubdir) -> $($target.Name)"
    return $target.FullName
  } finally {
    $script:EaName = $prevName
    $script:EaMagic = $prevMagic
  }
}

function Attach-ForgeBridge(
  [string]$DataPath,
  [string]$XmInstallPath,
  [bool]$TradingEnabled,
  [int]$InpMode = 0,
  [string]$BridgeSubdir = $BridgeSubdirLive
) {
  Stop-XmTerminal $XmInstallPath
  $chart = Write-ForgeBridgeToChart $DataPath $TradingEnabled $InpMode $BridgeSubdir $EaName $EaMagic
  if (-not $NoRestartTerminal) {
    Start-Process -FilePath (Join-Path $XmInstallPath "terminal64.exe")
    Start-Sleep -Seconds 8
  }
  return $chart
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
    "--monitor-port 9095 --bridge-dir `"$ProjectBridge`""
  )
  $created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create `
    -Arguments @{ CommandLine = $commandLine; CurrentDirectory = $RepoRoot }
  if ($created.ReturnValue -ne 0) {
    throw "Cannot create Bridge service (Win32 return=$($created.ReturnValue))."
  }
  if ($created.ProcessId) {
    [System.IO.File]::WriteAllText($pidFile, [string]$created.ProcessId)
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
if ($IsBoth -or $IsHistoryFeed) {
  $bridgeLinkSim = Ensure-NamedBridgeJunction $TerminalDataPath $BridgeSubdirSim $ProjectBridgeSim
  Write-Host "Sim     : $bridgeLinkSim -> $ProjectBridgeSim"
}
if ($IsBoth -or -not $IsHistoryFeed) {
  $bridgeLink = Ensure-BridgeJunction $TerminalDataPath
  Write-Host "Live    : $bridgeLink -> $ProjectBridge"
} elseif ($IsHistoryFeed) {
  try {
    $liveLink = Ensure-BridgeJunction $TerminalDataPath
    Write-Host "Live    : $liveLink -> $ProjectBridge"
  } catch {
    Write-Warning "Live bridge junction skipped: $($_.Exception.Message)"
  }
}

if ($IsBoth) {
  Write-Step "Copy and compile $EaNameLive + $EaNameSim"
  $compiledLive = Compile-OneEa $TerminalDataPath $InstallPath $SourceEaLive $EaNameLive
  Write-Host "EX5 Live: $($compiledLive.Binary)"
  $compiledSim = Compile-OneEa $TerminalDataPath $InstallPath $SourceEaSim $EaNameSim
  Write-Host "EX5 Sim : $($compiledSim.Binary)"
} else {
  Write-Step "Copy and compile $EaName"
  $compiled = Compile-Ea $TerminalDataPath $InstallPath
  Write-Host "EX5     : $($compiled.Binary)"
}

$attached = Get-ForgeBridgeCharts $TerminalDataPath
if ($Attach) {
  if ($IsBoth) {
    Write-Step "Attach Live + Simulate (single MT5 restart)"
    Stop-XmTerminal $InstallPath
    $chartLive = Write-ForgeBridgeToChart `
      $TerminalDataPath $EnableTrading.IsPresent 0 $BridgeSubdirLive $EaNameLive $EaMagicLive
    Write-Host "Live chart : $chartLive | Trading=$($EnableTrading.IsPresent)"
    $chartSim = Write-ForgeBridgeToChart `
      $TerminalDataPath $false 2 $BridgeSubdirSim $EaNameSim $EaMagicSim
    Write-Host "Sim chart  : $chartSim | HISTORY_FEED"
    if (-not $NoRestartTerminal) {
      Start-Process -FilePath (Join-Path $InstallPath "terminal64.exe")
      Start-Sleep -Seconds 8
    }
  } elseif ($IsHistoryFeed) {
    Write-Step "Attach $EaName HISTORY_FEED to GBPUSD M5"
    $chart = Attach-ForgeBridge $TerminalDataPath $InstallPath $false 2 $BridgeSubdirSim
    Write-Host "Chart   : $chart"
    Write-Host "Inputs  : InpMode=2 (HISTORY_FEED), InpBridgeSubdir=$BridgeSubdirSim, paper fills"
  } else {
    Write-Step "Attach $EaName Live to GBPUSD M5"
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
if ($IsBoth) {
  Write-Host "Live + Simulate ready (one MT5 restart). Start service / Start feed as needed."
} elseif ($IsHistoryFeed) {
  Write-Host "History Feed ready: App Simulate -> Start feed (sim_control.json)."
} else {
  Write-Host "Live ready. For Simulate: -Mode HistoryFeed -Attach  |  Both: -Mode Both -Attach -EnableTrading"
}
Write-Host "Next update command:"
Write-Host "powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`""
