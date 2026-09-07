# Deploy shared ForgeBridgeLive (+ Sim) to XM Global MT5.
# Defaults: Attach + EnableTrading (parity with Final_app manage DeployEA).
#
#   .\deploy_live_ea.ps1
#   .\deploy_live_ea.ps1 -FromRoster          # all enabled books (one MT5 restart)
#   .\deploy_live_ea.ps1 -Mode Both
#   .\deploy_live_ea.ps1 -NoAttach
#   .\deploy_live_ea.ps1 -Symbol EURUSD -Timeframe M5
#   # Called from Live Start (Python): -FromRoster -SkipBridgeService -Attach -EnableTrading
#
[CmdletBinding()]
param(
  [string]$TerminalDataPath = "",
  [string]$InstallPath = "",
  [string]$ModelId = "",
  [string]$Symbol = "",
  [ValidateSet("", "M5", "M15")]
  [string]$Timeframe = "",
  [double]$RiskPct = 1.0,
  [double]$PollSeconds = 2.0,
  [ValidateSet("Live", "HistoryFeed", "Both")]
  [string]$Mode = "Live",
  [switch]$FromRoster,
  [switch]$Attach,
  [switch]$NoAttach,
  [switch]$EnableTrading,
  [switch]$NoEnableTrading,
  [switch]$RestartTerminal,
  [switch]$NoRestartTerminal,
  [bool]$StartBridgeService = $true,
  [switch]$SkipBridgeService
)

$ErrorActionPreference = "Stop"
$LiveRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SplitRoot = (Resolve-Path (Join-Path $LiveRoot "..")).Path
$RepoRoot = $SplitRoot  # mt5/Experts + bridge_* live under split_app
$SourceEaLive = Join-Path $RepoRoot "mt5\Experts\ForgeBridgeLive.mq5"
$SourceEaSim = Join-Path $RepoRoot "mt5\Experts\ForgeBridgeLiveSim.mq5"
$ProjectBridge = Join-Path $RepoRoot "mt5\bridge_live"
$ProjectBridgeSim = Join-Path $RepoRoot "mt5\bridge_sim_live"
$BridgeSubdirLive = "bridge_live"
$BridgeSubdirSim = "bridge_sim_live"
$EaNameLive = "ForgeBridgeLive"
$EaNameSim = "ForgeBridgeLiveSim"
$EaFolder = "EdgeMinerLive2"
$EaMagicLive = 20283001
$EaMagicSim = 20284001
$IsBoth = ($Mode -eq "Both")

# Defaults: Attach + EnableTrading (like Final_app manage DeployEA)
$doAttach = -not $NoAttach.IsPresent
if ($Attach.IsPresent) { $doAttach = $true }
$doTrading = -not $NoEnableTrading.IsPresent
if ($EnableTrading.IsPresent) { $doTrading = $true }
if ($doAttach) { $Attach = $true } else { $Attach = $false }
if ($doTrading) { $EnableTrading = $true } else { $EnableTrading = $false }

function Get-BookKey([string]$Sym, [string]$Tf) {
  return ("{0}_{1}" -f $Sym.ToLowerInvariant(), $Tf.ToLowerInvariant())
}

function Get-EnabledBooksFromRoster([string]$RosterFile) {
  if (-not (Test-Path $RosterFile)) { return @() }
  $roster = Get-Content $RosterFile -Raw | ConvertFrom-Json
  $enabled = @($roster.models | Where-Object { $_.enabled })
  $map = @{}
  foreach ($row in $enabled) {
    $sym = ([string]$row.symbol).Trim().ToUpperInvariant()
    $tf = ([string]$row.timeframe).Trim().ToUpperInvariant()
    if (-not $sym -or -not $tf) { continue }
    $key = Get-BookKey $sym $tf
    if (-not $map.ContainsKey($key)) {
      $magic = $null
      try {
        if ($null -ne $row.magic) { $magic = [int]$row.magic }
      } catch {
        $magic = $null
      }
      $risk = 1.0
      try {
        if ($null -ne $row.risk_pct) { $risk = [double]$row.risk_pct }
      } catch {
        $risk = 1.0
      }
      $period = 5
      if ($tf -eq "M15") { $period = 15 }
      $entry = New-Object psobject -Property @{
        Symbol = $sym
        Timeframe = $tf
        PeriodSize = $period
        BridgeSubdir = ("bridge_live_{0}" -f $key)
        ProjectDir = Join-Path $RepoRoot ("mt5\bridge_live_{0}" -f $key)
        Magic = $magic
        RiskPct = $risk
        ModelIds = @([string]$row.model_id)
      }
      $map[$key] = $entry
    } else {
      $map[$key].ModelIds += [string]$row.model_id
      if ($null -eq $map[$key].Magic -and $null -ne $row.magic) {
        try { $map[$key].Magic = [int]$row.magic } catch { }
      }
    }
  }
  return @($map.Values)
}

# Resolve Symbol/Timeframe from live_roster.json when not passed
$RosterPath = Join-Path $LiveRoot "results\live_roster.json"
$RosterBooks = @()
if (Test-Path $RosterPath) {
  try { $RosterBooks = @(Get-EnabledBooksFromRoster $RosterPath) } catch { $RosterBooks = @() }
}
# Auto multi-book when -FromRoster, or when Symbol/TF omitted and roster has books
$useFromRoster = [bool]$FromRoster.IsPresent
if ((-not $Symbol -or -not $Timeframe) -and $RosterBooks.Count -gt 0 -and $Mode -eq "Live") {
  $useFromRoster = $true
}
if ((-not $Symbol -or -not $Timeframe) -and $RosterBooks.Count -gt 0) {
  if (-not $Symbol) { $Symbol = [string]$RosterBooks[0].Symbol }
  if (-not $Timeframe) { $Timeframe = [string]$RosterBooks[0].Timeframe }
}
if (-not $Symbol) { $Symbol = "EURUSD" }
if (-not $Timeframe) { $Timeframe = "M5" }
$PeriodSize = if ($Timeframe -eq "M15") { 15 } else { 5 }
if ($useFromRoster -and $Mode -eq "Live" -and $RosterBooks.Count -eq 0) {
  throw "FromRoster: no enabled models in $RosterPath"
}
if ($useFromRoster -and $Mode -eq "Live") {
  Write-Host ("Live DeployEA FromRoster books={0} Attach={1} Trading={2}" -f $RosterBooks.Count, $Attach, $EnableTrading) -ForegroundColor Cyan
  foreach ($b in $RosterBooks) {
    Write-Host ("  - {0} {1} subdir={2} models={3}" -f $b.Symbol, $b.Timeframe, $b.BridgeSubdir, ($b.ModelIds -join ","))
  }
} else {
  Write-Host ("Live DeployEA Symbol={0} TF={1} period_size={2} Attach={3} Trading={4}" -f $Symbol, $Timeframe, $PeriodSize, $Attach, $EnableTrading) -ForegroundColor Cyan
}

# Sync Python roster -> models.json before compile/attach
$pyCandidates = @(
  "C:\Work\ThuyenRepo\EdgeMinerM15B5\.venv\Scripts\python.exe",
  "python"
)
$py = $pyCandidates | Where-Object { $_ -eq "python" -or (Test-Path $_) } | Select-Object -First 1
& $py (Join-Path $LiveRoot "sync_bridge_roster.py")
if ($LASTEXITCODE -ne 0) { throw "sync_bridge_roster.py failed" }

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
    Write-Warning "No ModelId - relying on live_roster / models.json multi-model roster."
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
  throw 'XM Global MT5 not found. Pass -InstallPath with the MT5 install folder.'
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
    Write-Warning ("Relinking {0} from '{1}' -> '{2}'" -f $link, ($targets -join ', '), $ProjectTarget)
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

function Get-TargetCharts([string]$DataPath) {
  $chartsRoot = Get-ActiveChartsRoot $DataPath
  $sym = [regex]::Escape($Symbol)
  $allSymCharts = Get-ChildItem $chartsRoot -Filter "*.chr" -Recurse |
    Where-Object {
      $text = Get-Content $_.FullName -Raw
      $text -match ("(?m)^symbol=" + $sym + "\s*$")
    }
  $charts = $allSymCharts |
    Where-Object {
      $text = Get-Content $_.FullName -Raw
      $text -match "(?m)^period_type=0\s*$" -and
      $text -match ("(?m)^period_size=" + $PeriodSize + "\s*$")
    }
  return @($charts)
}

function New-MinimalTargetChartText(
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
      (Get-Content $_.FullName -Raw) -match "(?m)^symbol=$Symbol\s*$"
    })
  if ($all.Count -eq 0) { return $null }
  $free = @($all | Where-Object {
    (Get-Content $_.FullName -Raw) -notmatch $family
  } | Select-Object -First 1)
  if ($free.Count -gt 0) { return $free[0] }
  return $all[0]
}

function New-TargetChart([string]$DataPath) {
  $chartsRoot = Get-ActiveChartsRoot $DataPath
  $family = Get-ForgeFamilyPattern
  $templates = @(Get-ChildItem $chartsRoot -Filter "*.chr" -ErrorAction SilentlyContinue |
    Where-Object {
      (Get-Content $_.FullName -Raw) -match "(?m)^symbol=$Symbol\s*$"
    })
  # Active profile empty (e.g. Default with 0 charts) - borrow EURUSD from any profile.
  if ($templates.Count -eq 0) {
    $borrowed = Find-EurusdChartTemplate $DataPath
    if ($borrowed) {
      Write-Host ("No EURUSD in active profile; template from {0}\{1}" -f $borrowed.Directory.Name, $borrowed.Name)
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
    Write-Host "No chart template anywhere - creating blank $Symbol $Timeframe chart."
    $text = New-MinimalTargetChartText 0 $PeriodSize
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
    $text = $text -replace '(?m)^period_size=\d+\s*$', ("period_size=" + $PeriodSize)
    # Match every ForgeBridge* (stock M15/H1 + clones M15B4/M15B5/...) so we never
    # copy a sibling instance's expert onto a new chart template.
    $forgeExpertPattern = '(?s)<expert>\s*name=ForgeBridge[A-Za-z0-9]*\b.*?</expert>\s*'
    $text = [regex]::Replace($text, $forgeExpertPattern, '')
  }
  Set-Content -Path $targetPath -Value $text -Encoding Unicode
  Write-Host "Created $Symbol $Timeframe chart in active profile: $targetPath"
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
    'InpChartBars=4032',
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
  # ForgeBridgeM5F3\b does not match ForgeBridgeM5F3B4 - must use the open suffix.
  return 'name=ForgeBridge[A-Za-z0-9]*\b'
}

function Select-AttachChart(
  [string]$DataPath,
  [bool]$PreferHistoryFeed
) {
  $charts = Get-TargetCharts $DataPath
  if (-not $charts -or $charts.Count -eq 0) {
    $charts = @(New-TargetChart $DataPath)
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
    Write-Host "Attach target: free $Symbol $Timeframe chart $($free[0].Name) for $wantedName"
    return $free[0]
  }

  # 3) All M15 charts already have a ForgeBridge* EA - create a new chart
  #    (clone template, strip experts) instead of overwriting Live <-> Sim.
  Write-Host "No free $Symbol $Timeframe chart for $wantedName; creating a new chart (keep $otherName intact)."
  $created = @(New-TargetChart $DataPath)
  if ($created.Count -eq 0) {
    throw ("Failed to create $Symbol $Timeframe chart for $wantedName.")
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
    $text = $text -replace '(?m)^period_size=\d+\s*$', ("period_size=" + $PeriodSize)
    $forgeExpertPattern = '(?s)<expert>\s*name=ForgeBridge[A-Za-z0-9]*\b.*?</expert>\s*'
    $windowTag = '<window>'
    $text = [regex]::Replace($text, $forgeExpertPattern, '')
    if ($text -notmatch [regex]::Escape($windowTag)) {
      if ($text -notmatch '</chart>') {
        throw ("Chart {0} has neither window nor chart closing tag; cannot attach {1}." -f $target.FullName, $ExpertName)
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
  $pidFile = Join-Path $LiveRoot "results\mt5_bridge_service.pid"
  $configFile = Join-Path $LiveRoot "results\mt5_bridge_config.json"
  $logFile = Join-Path $LiveRoot "results\mt5_bridge_service.log"
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
  $escapedLive = [regex]::Escape($LiveRoot)
  $escapedBridge = [regex]::Escape($ProjectBridge)
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.CommandLine -match "mt5_bridge_service_live\.py" -and
      ($_.CommandLine -match $escapedLive -or $_.CommandLine -match $escapedBridge)
    } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
  Start-Sleep -Milliseconds 500
  if (Test-Path $pidFile) {
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
  }

  # Prefer Live Python bridge_control (materialize + start).
  # Skip nested auto-deploy (this script already attached EAs).
  $stopCmd = "import bridge_control; bridge_control.stop_bridge()"
  & $py -c $stopCmd 2>$null
  Push-Location $LiveRoot
  try {
    $env:LIVE_SKIP_EA_DEPLOY = "1"
    & $py -c "import bridge_control; print(bridge_control.start_bridge(poll_sec=$PollSeconds)['pid'])"
    if ($LASTEXITCODE -ne 0) { throw "bridge_control.start_bridge failed" }
  } finally {
    Remove-Item Env:LIVE_SKIP_EA_DEPLOY -ErrorAction SilentlyContinue
    Pop-Location
  }

  Start-Sleep -Seconds 4
  if (-not (Test-Path $pidFile)) {
    throw "Bridge service did not create a PID file. Check $logFile"
  }
  $newPid = [int](Get-Content $pidFile -Raw)
  if (-not (Get-Process -Id $newPid -ErrorAction SilentlyContinue)) {
    throw "Bridge service PID $newPid is not running. Check $logFile"
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
if ($useFromRoster -and $Mode -eq "Live") {
  foreach ($b in $RosterBooks) {
    New-Item -ItemType Directory -Path $b.ProjectDir -Force | Out-Null
    $link = Ensure-NamedBridgeJunction $TerminalDataPath $b.BridgeSubdir $b.ProjectDir
    Write-Host ("Live    : {0} -> {1}" -f $link, $b.ProjectDir)
  }
  # Legacy default subdir -> first book (old EA input default bridge_live)
  if ($RosterBooks.Count -gt 0) {
    $legacy = Ensure-NamedBridgeJunction $TerminalDataPath $BridgeSubdirLive $RosterBooks[0].ProjectDir
    Write-Host "Legacy  : $legacy -> $($RosterBooks[0].ProjectDir)"
  }
} elseif ($IsBoth -or -not $IsHistoryFeed) {
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
  if ($useFromRoster -and $Mode -eq "Live") {
    Write-Step ("Attach Live EA for {0} book(s) (single MT5 restart)" -f $RosterBooks.Count)
    Stop-XmTerminal $InstallPath
    $attachedPaths = @()
    foreach ($b in $RosterBooks) {
      $script:Symbol = [string]$b.Symbol
      $script:Timeframe = [string]$b.Timeframe
      $script:PeriodSize = [int]$b.PeriodSize
      $script:RiskPct = [double]$b.RiskPct
      $mag = if ($null -ne $b.Magic) { [int]$b.Magic } else { [int]$EaMagicLive }
      Write-Host ("Attaching {0} {1} InpBridgeSubdir={2} magic={3}" -f $b.Symbol, $b.Timeframe, $b.BridgeSubdir, $mag)
      $chartPath = Write-ForgeBridgeToChart `
        $TerminalDataPath $doTrading 0 $b.BridgeSubdir $EaNameLive $mag
      $attachedPaths += $chartPath
      Write-Host "  -> $chartPath | Trading=$doTrading"
    }
    if (-not $NoRestartTerminal) {
      Start-Process -FilePath (Join-Path $InstallPath "terminal64.exe")
      Start-Sleep -Seconds 8
    }
    $attached = @($attachedPaths)
  } elseif ($IsBoth) {
    Write-Step "Attach Live + Simulate (single MT5 restart)"
    Stop-XmTerminal $InstallPath
    $chartLive = Write-ForgeBridgeToChart `
      $TerminalDataPath $doTrading 0 $BridgeSubdirLive $EaNameLive $EaMagicLive
    Write-Host "Live chart : $chartLive | Trading=$doTrading"
    $chartSim = Write-ForgeBridgeToChart `
      $TerminalDataPath $false 2 $BridgeSubdirSim $EaNameSim $EaMagicSim
    Write-Host "Sim chart  : $chartSim | HISTORY_FEED"
    if (-not $NoRestartTerminal) {
      Start-Process -FilePath (Join-Path $InstallPath "terminal64.exe")
      Start-Sleep -Seconds 8
    }
  } elseif ($IsHistoryFeed) {
    Write-Step "Attach $EaName HISTORY_FEED to $Symbol $Timeframe"
    $chart = Attach-ForgeBridge $TerminalDataPath $InstallPath $false 2 $BridgeSubdirSim
    Write-Host "Chart   : $chart"
    Write-Host "Inputs  : InpMode=2 (HISTORY_FEED), InpBridgeSubdir=$BridgeSubdirSim, paper fills"
  } else {
    # Single-book Live: prefer per-book subdir when roster known
    $liveSub = $BridgeSubdirLive
    $liveProj = $ProjectBridge
    $liveMagic = $EaMagicLive
    if ($RosterBooks.Count -gt 0) {
      $match = @($RosterBooks | Where-Object {
        $_.Symbol -eq $Symbol -and $_.Timeframe -eq $Timeframe
      } | Select-Object -First 1)
      if ($match.Count -gt 0) {
        $liveSub = $match[0].BridgeSubdir
        $liveProj = $match[0].ProjectDir
        if ($null -ne $match[0].Magic) { $liveMagic = [int]$match[0].Magic }
        New-Item -ItemType Directory -Path $liveProj -Force | Out-Null
        Ensure-NamedBridgeJunction $TerminalDataPath $liveSub $liveProj | Out-Null
      }
    }
    Write-Step "Attach $EaName Live to $Symbol $Timeframe (subdir=$liveSub)"
    $script:EaMagic = $liveMagic
    $chart = Attach-ForgeBridge $TerminalDataPath $InstallPath $doTrading 0 $liveSub
    Write-Host "Chart   : $chart"
    Write-Host "Trading : $doTrading"
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
if ($useFromRoster -and $Mode -eq "Live") {
  Write-Host ("Live ready for {0} book(s) from roster (one MT5 restart)." -f $RosterBooks.Count)
} elseif ($IsBoth) {
  Write-Host "Live + Simulate ready (one MT5 restart). Start service / Start feed as needed."
} elseif ($IsHistoryFeed) {
  Write-Host "History Feed ready: App Simulate -> Start feed (sim_control.json)."
} else {
  Write-Host "Live ready. For Simulate: -Mode HistoryFeed -Attach  |  Both: -Mode Both -Attach -EnableTrading"
  Write-Host "Multi-book: -FromRoster -Attach -EnableTrading -SkipBridgeService"
}
Write-Host "Next update command:"
Write-Host "powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -FromRoster"
