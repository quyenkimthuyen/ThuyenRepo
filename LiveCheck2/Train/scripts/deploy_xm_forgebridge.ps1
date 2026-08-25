[CmdletBinding()]
param(
  [string]$Desk = "",
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
$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Get-DeskYamlMap([string]$Path) {
  $map = @{}
  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf(":")
    if ($idx -lt 1) { return }
    $key = $line.Substring(0, $idx).Trim()
    $val = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
    $hash = $val.IndexOf(" #")
    if ($hash -ge 0) { $val = $val.Substring(0, $hash).Trim() }
    $map[$key] = $val
  }
  return $map
}

if (-not $Desk) { $Desk = [string]$env:TRAINAPP_DESK }
$Desk = "$Desk".Trim().ToLowerInvariant()
if (-not $Desk) {
  throw "Desk not set. Pass -Desk e21|g23 or set TRAINAPP_DESK."
}
$deskFile = Join-Path $AppRoot "desks\$Desk.yaml"
if (-not (Test-Path -LiteralPath $deskFile)) {
  throw "Desk config missing: $deskFile"
}
$yaml = Get-DeskYamlMap $deskFile
$InstanceId = [string]$yaml["instance_id"]
$CoreName = [string]$yaml["core"]
$Symbol = [string]$yaml["symbol"]
$TfLabel = [string]$yaml["tf"]
$BridgeSubdirLive = [string]$yaml["bridge_subdir"]
if (-not $InstanceId) { throw "desks\$Desk.yaml missing instance_id" }
if (-not $CoreName) { throw "desks\$Desk.yaml missing core" }
if (-not $Symbol) { throw "desks\$Desk.yaml missing symbol" }
if (-not $TfLabel) { $TfLabel = "M15" }
if (-not $BridgeSubdirLive) { $BridgeSubdirLive = "bridge_$($InstanceId.ToLowerInvariant())" }

$PeriodSize = 15
if ($yaml.ContainsKey("bar_minutes") -and $yaml["bar_minutes"]) {
  $PeriodSize = [int]$yaml["bar_minutes"]
} elseif ($TfLabel -match "(\d+)$") {
  $PeriodSize = [int]$Matches[1]
}
$ChartBars = if ($PeriodSize -le 5) { 4032 } else { 1344 }
$MonitorPort = if ($PeriodSize -le 5) { 9075 } else { 8975 }

function Test-PathUnder([string]$Child, [string]$Parent) {
  if (-not $Child -or -not $Parent) { return $false }
  $c = [System.IO.Path]::GetFullPath($Child).TrimEnd("\")
  $p = [System.IO.Path]::GetFullPath($Parent).TrimEnd("\")
  return $c.Equals($p, [System.StringComparison]::OrdinalIgnoreCase) -or
    $c.StartsWith($p + "\", [System.StringComparison]::OrdinalIgnoreCase)
}

$RepoRoot = [string]$env:TRAINAPP_RUNTIME
if (-not $RepoRoot -or -not (Test-PathUnder $RepoRoot $AppRoot)) {
  $RepoRoot = Join-Path $AppRoot "runtime\$Desk"
}
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
if (-not (Test-Path -LiteralPath $RepoRoot)) {
  throw "Runtime folder missing: $RepoRoot"
}
$CoreRoot = [string]$env:TRAINAPP_CORE
if (-not $CoreRoot -or -not (Test-PathUnder $CoreRoot $AppRoot)) {
  $CoreRoot = Join-Path $AppRoot "cores\$CoreName"
}
$CoreRoot = [System.IO.Path]::GetFullPath($CoreRoot)
if (-not (Test-Path -LiteralPath $CoreRoot)) {
  throw "Core folder missing: $CoreRoot"
}

$env:TRAINAPP_DESK = $Desk
$env:TRAINAPP_RUNTIME = $RepoRoot
$env:TRAINAPP_CORE = $CoreRoot
$env:TRAINAPP_ROOT = $AppRoot
$pyParts = @($AppRoot, $CoreRoot)
if ($env:PYTHONPATH) { $pyParts += $env:PYTHONPATH }
$env:PYTHONPATH = ($pyParts -join ";")

$EaNameLive = "ForgeBridge$InstanceId"
$SourceEaLive = Join-Path $RepoRoot "mt5\Experts\$EaNameLive.mq5"
$ProjectBridge = Join-Path $RepoRoot "mt5\$BridgeSubdirLive"
$EaFolder = "EdgeMiner$InstanceId"
$EaMagicLive = if ($yaml["magic"]) { [int]$yaml["magic"] } else { 0 }
# One Live EA only: history test uses sim_control.json on the Live bridge folder.
if ($Mode -eq "HistoryFeed" -or $Mode -eq "Both") {
  Write-Host "One Live EA: -Mode $Mode is treated as Live (history test uses sim_control.json)."
  $Mode = "Live"
}
$EaName = $EaNameLive
$SourceEa = $SourceEaLive
$EaMagic = $EaMagicLive
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

function Get-EurusdM15Charts([string]$DataPath) {
  $chartsRoot = Get-ActiveChartsRoot $DataPath
  $allEurusdCharts = Get-ChildItem $chartsRoot -Filter "*.chr" -Recurse |
    Where-Object {
      $text = Get-Content $_.FullName -Raw
      $text -match ("(?m)^symbol=" + [regex]::Escape($Symbol) + "\s*$")
    }
  $charts = $allEurusdCharts |
    Where-Object {
      $text = Get-Content $_.FullName -Raw
      $text -match "(?m)^period_type=0\s*$" -and
      $text -match ("(?m)^period_size=" + $PeriodSize + "\s*$")
    }
  return @($charts)
}

function New-MinimalEurusdChartText(
  [int]$PeriodType,
  [int]$PeriodSize
) {
  $id = [DateTime]::UtcNow.Ticks
  $lines = @(
    '<chart>',
    "id=$id",
    "symbol=$Symbol",
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

function Find-EurusdChartTemplate([string]$DataPath) {
  $chartsBase = Join-Path $DataPath "MQL5\Profiles\Charts"
  if (-not (Test-Path $chartsBase)) { return $null }
  $family = Get-ForgeFamilyPattern
  $all = @(Get-ChildItem $chartsBase -Filter "*.chr" -Recurse -ErrorAction SilentlyContinue |
    Where-Object {
      (Get-Content $_.FullName -Raw) -match ("(?m)^symbol=" + [regex]::Escape($Symbol) + "\s*$")
    })
  if ($all.Count -eq 0) { return $null }
  $free = @($all | Where-Object {
    (Get-Content $_.FullName -Raw) -notmatch $family
  } | Select-Object -First 1)
  if ($free.Count -gt 0) { return $free[0] }
  return $all[0]
}

function New-EurusdM15Chart([string]$DataPath) {
  $chartsRoot = Get-ActiveChartsRoot $DataPath
  $family = Get-ForgeFamilyPattern
  $templates = @(Get-ChildItem $chartsRoot -Filter "*.chr" -ErrorAction SilentlyContinue |
    Where-Object {
      (Get-Content $_.FullName -Raw) -match ("(?m)^symbol=" + [regex]::Escape($Symbol) + "\s*$")
    })
  # Active profile empty (e.g. Default with 0 charts) - borrow EURUSD from any profile.
  if ($templates.Count -eq 0) {
    $borrowed = Find-EurusdChartTemplate $DataPath
    if ($borrowed) {
      Write-Host "No $Symbol in active profile; using template from $($borrowed.Directory.Name)\$($borrowed.Name)"
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
    Write-Host "No $Symbol template anywhere - creating blank $Symbol $TfLabel chart."
    $text = New-MinimalEurusdChartText 0 $PeriodSize
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
    $text = $text -replace '(?m)^period_size=\d+\s*$', "period_size=$PeriodSize"
    # Match every ForgeBridge* (stock M15/H1 + clones M15B4/M15B5/...) so we never
    # copy a sibling instance's expert onto a new chart template.
    $forgeExpertPattern = '(?s)<expert>\s*name=ForgeBridge[A-Za-z0-9]*\b.*?</expert>\s*'
    $text = [regex]::Replace($text, $forgeExpertPattern, '')
  }
  Set-Content -Path $targetPath -Value $text -Encoding Unicode
  Write-Host "Created $Symbol $TfLabel chart in active profile: $targetPath"
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
    "InpChartBars=$ChartBars",
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
  # Charts owned by ANY ForgeBridge instance (including sibling clones) are not free.
  # ForgeBridgeM15E21\b does not match ForgeBridgeM15E21B4 — must use the open suffix.
  return 'name=ForgeBridge[A-Za-z0-9]*\b'
}

function Select-AttachChart(
  [string]$DataPath
) {
  $charts = Get-EurusdM15Charts $DataPath
  if (-not $charts -or $charts.Count -eq 0) {
    $charts = @(New-EurusdM15Chart $DataPath)
  }

  $wantedName = $EaNameLive
  $family = Get-ForgeFamilyPattern

  # 1) Re-attach only the chart that already has THIS EA name.
  $same = @($charts | Where-Object {
    (Get-Content $_.FullName -Raw) -match ("name=" + [regex]::Escape($wantedName))
  })
  if ($same.Count -gt 0) {
    Write-Host "Attach target: existing $wantedName on $($same[0].Name)"
    return $same[0]
  }

  # 2) Prefer a chart with no ForgeBridge* EA (do not touch other TF EAs).
  $free = @($charts | Where-Object {
    (Get-Content $_.FullName -Raw) -notmatch $family
  })
  if ($free.Count -gt 0) {
    Write-Host "Attach target: free $Symbol $TfLabel chart $($free[0].Name) for $wantedName"
    return $free[0]
  }

  # 3) All charts already have a ForgeBridge* EA — create a new chart.
  Write-Host "No free $Symbol $TfLabel chart for $wantedName; creating a new chart."
  $created = @(New-EurusdM15Chart $DataPath)
  if ($created.Count -eq 0) {
    throw ("Failed to create $Symbol $TfLabel chart for $wantedName.")
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
    $target = Select-AttachChart $DataPath
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item $target.FullName "$($target.FullName).backup_$timestamp" -Force
    $block = New-ForgeBridgeExpertBlock $TradingEnabled $InpMode $BridgeSubdir

    $text = Get-Content $target.FullName -Raw
    $text = $text -replace '(?m)^period_type=\d+\s*$', 'period_type=0'
    $text = $text -replace '(?m)^period_size=\d+\s*$', "period_size=$PeriodSize"
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

function ConvertTo-QuotedArgumentLine([string[]]$Parts) {
  # PS 5.1 Start-Process -ArgumentList @{array} re-splits on spaces/commas.
  # One quoted command line matches CreateProcess parsing.
  ($Parts | ForEach-Object {
    $p = [string]$_
    if ($null -eq $p) { return '""' }
    if ($p -match '^[A-Za-z0-9_.:\\/+=,-]+$') { $p }
    else { '"' + ($p -replace '"', '\"') + '"' }
  }) -join ' '
}

function Restart-BridgeService {
  $pidFile = Join-Path $RepoRoot "results\mt5_bridge_service.pid"
  $configFile = Join-Path $RepoRoot "results\mt5_bridge_config.json"
  $logFile = Join-Path $RepoRoot "results\mt5_bridge_service.log"
  $outFile = Join-Path $RepoRoot "results\mt5_bridge_service.launch.out"
  $errFile = Join-Path $RepoRoot "results\mt5_bridge_service.launch.err"
  New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "results") | Out-Null

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

  # Keep enabled=true *before* spawn. Setting false first let the Streamlit
  # watchdog / service loop kill the new PID during the wait.
  # Do not ConvertTo-Json the whole file: PS 5.1 collapses one-item arrays.
  if (Test-Path $configFile) {
    try {
      $raw = [System.IO.File]::ReadAllText($configFile)
      if ($raw -match '"enabled"\s*:') {
        $raw = [regex]::Replace($raw, '"enabled"\s*:\s*(false|true)', '"enabled": true')
        [System.IO.File]::WriteAllText($configFile, $raw)
      }
    } catch {
      Write-Warning "Could not update Bridge config enabled=true: $($_.Exception.Message)"
    }
  }

  $python = (Get-Command python -ErrorAction Stop).Source
  $servicePy = Join-Path $CoreRoot "scripts\mt5_bridge_service.py"
  if (-not (Test-Path -LiteralPath $servicePy)) {
    throw "Bridge service script not found: $servicePy"
  }
  foreach ($f in @($outFile, $errFile)) {
    if (Test-Path $f) { Remove-Item $f -Force -ErrorAction SilentlyContinue }
  }
  try {
    Add-Content -Path $logFile -Value "`n--- start $(Get-Date -Format o) (deploy) ---"
  } catch {}

  # Start-Process + Redirect inherits $env:PYTHONPATH / TRAINAPP_*.
  # CIM process Create does not — that is why the PID died with no log line.
  $argLine = ConvertTo-QuotedArgumentLine @(
    "-u"
    $servicePy
    "--model-id", "$ModelId"
    "--model-ids", "$ModelId"
    "--risk-pct", "$RiskPct"
    "--poll", "$PollSeconds"
    "--monitor-port", "$MonitorPort"
    "--bridge-dir", "$ProjectBridge"
  )
  $proc = Start-Process -FilePath $python -ArgumentList $argLine `
    -WorkingDirectory $RepoRoot `
    -PassThru `
    -RedirectStandardOutput $outFile `
    -RedirectStandardError $errFile
  if (-not $proc) {
    throw "Cannot start Bridge service (Start-Process returned no process)."
  }
  [System.IO.File]::WriteAllText($pidFile, [string]$proc.Id)

  Start-Sleep -Seconds 8
  if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
    $detail = New-Object System.Collections.Generic.List[string]
    foreach ($f in @($errFile, $outFile, $logFile)) {
      if (Test-Path $f) {
        $tail = @(Get-Content $f -Tail 40 -ErrorAction SilentlyContinue)
        if ($tail.Count -gt 0) {
          [void]$detail.Add("--- $(Split-Path $f -Leaf) ---")
          $tail | ForEach-Object { [void]$detail.Add($_) }
        }
      }
    }
    $msg = "Bridge service PID $($proc.Id) is not running."
    if ($detail.Count -gt 0) { $msg += "`n" + ($detail -join "`n") }
    throw $msg
  }
  try {
    if (Test-Path $outFile) { Get-Content $outFile -ErrorAction SilentlyContinue | Add-Content $logFile }
    if (Test-Path $errFile) { Get-Content $errFile -ErrorAction SilentlyContinue | Add-Content $logFile }
  } catch {}
  return $proc.Id
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
Write-Host "Desk    : $Desk ($InstanceId $Symbol $TfLabel)"
Write-Host "Runtime : $RepoRoot"
Write-Host "Mode    : $Mode"

Write-Step "Link MQL5 Files to app"
$bridgeLink = Ensure-BridgeJunction $TerminalDataPath
Write-Host "Live    : $bridgeLink -> $ProjectBridge"

Write-Step "Render ForgeBridge EA v1.25 for desk $Desk"
$renderScript = Join-Path $AppRoot "scripts\render_forgebridge_ea.py"
if (Test-Path -LiteralPath $renderScript) {
  $py = (Get-Command python -ErrorAction SilentlyContinue).Source
  if ($py) {
    & $py $renderScript --desk $Desk
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "render_forgebridge_ea.py failed (exit=$LASTEXITCODE) — using existing .mq5"
    }
  }
} else {
  Write-Warning "Missing $renderScript — skip EA render"
}

Write-Step "Copy and compile $EaName"
$compiled = Compile-Ea $TerminalDataPath $InstallPath
Write-Host "EX5     : $($compiled.Binary)"

$attached = Get-ForgeBridgeCharts $TerminalDataPath
if ($Attach) {
  Write-Step "Attach $EaName Live to $Symbol $TfLabel"
  $chart = Attach-ForgeBridge $TerminalDataPath $InstallPath $EnableTrading.IsPresent 0 $BridgeSubdirLive
  Write-Host "Chart   : $chart"
  Write-Host "Trading : $($EnableTrading.IsPresent)"
  Write-Host "History test: same EA + chart; App writes sim_control.json on $BridgeSubdirLive"
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
Write-Host "Live EA ready. History test: App from/to writes sim_control.json on this same chart (no Sim EX5)."
Write-Host "Next update command:"
Write-Host "powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Desk $Desk"
