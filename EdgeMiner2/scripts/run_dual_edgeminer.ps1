[CmdletBinding()]
param(
  [ValidateSet("Deploy", "Start", "Restart", "Stop", "Status")]
  [string]$Action = "Status"
)

$ErrorActionPreference = "Stop"
$M15Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$H1Root = "C:\Work\ThuyenRepo\EdgeMinerH1"
$M15AppPort = 8501
$H1AppPort = 8502
$Expected = @{
  M15 = @{ Period = "M15"; Magic = 20260724; Instance = "M15"; Bridge = "bridge" }
  H1 = @{ Period = "H1"; Magic = 20260725; Instance = "H1"; Bridge = "bridge_h1" }
}

function Assert-Layout {
  if (-not (Test-Path $H1Root)) { throw "H1 repo not found: $H1Root" }
  if ($M15Root -eq $H1Root) { throw "H1 and M15 roots must be different." }
  if ($Expected.M15.Magic -eq $Expected.H1.Magic) { throw "Magic numbers collide." }
  if ($Expected.M15.Bridge -eq $Expected.H1.Bridge) { throw "Bridge folders collide." }
  foreach ($root in @($M15Root, $H1Root)) {
    if (-not (Test-Path (Join-Path $root "results\active_trade_model.json"))) {
      throw "No active model in $root"
    }
  }
}

function Invoke-App([string]$Root, [string]$AppAction, [int]$Port) {
  & powershell -ExecutionPolicy Bypass -File (Join-Path $Root "scripts\run_app_windows.ps1") `
    -Action $AppAction -Port $Port
  if ($LASTEXITCODE -ne 0) { throw "App $AppAction failed in $Root" }
}

function Invoke-Python([string]$Root, [string]$Code) {
  Push-Location $Root
  try {
    & python -c $Code
    if ($LASTEXITCODE -ne 0) { throw "Python service command failed in $Root" }
  } finally {
    Pop-Location
  }
}

function Start-Services {
  Invoke-Python $M15Root "from mt5_bridge.background import save_config,start_worker; save_config(enabled=True,model_id='tm_m15_best_2_49216b56',risk_pct=1.0,poll_sec=2.0,bridge_dir=r'$M15Root\mt5\bridge'); assert start_worker()"
  Invoke-Python $H1Root "from mt5_bridge.background import save_config,start_worker; save_config(enabled=True,model_id='tm_mt5_best_94ef551a',risk_pct=1.0,poll_sec=2.0,bridge_dir=r'$H1Root\mt5\bridge_h1'); assert start_worker()"
  Invoke-Python $M15Root "from paper_service import save_config,start_worker; save_config(enabled=True,model_id='tm_m15_best_2_49216b56',risk_pct=1.0,poll_sec=2.0); assert start_worker()"
  Invoke-Python $H1Root "from paper_service import save_config,start_worker; save_config(enabled=True,model_id='tm_mt5_best_94ef551a',risk_pct=1.0,poll_sec=2.0); assert start_worker()"
}

function Stop-Services {
  Invoke-Python $M15Root "from paper_service import stop_worker; stop_worker(); from mt5_bridge.background import stop_worker as stop_bridge; stop_bridge()"
  Invoke-Python $H1Root "from paper_service import stop_worker; stop_worker(); from mt5_bridge.background import stop_worker as stop_bridge; stop_bridge()"
}

function Read-Connection([string]$Path, [hashtable]$Identity) {
  $deadline = (Get-Date).AddSeconds(30)
  do {
    if (Test-Path $Path) {
      try {
        $value = Get-Content $Path -Raw | ConvertFrom-Json
        if (
          $value.connected -and $value.hedging -and
          [int64]$value.account_margin_mode -eq 2 -and
          $value.period -eq $Identity.Period -and
          [int64]$value.magic -eq $Identity.Magic -and
          $value.instance_id -eq $Identity.Instance -and
          $value.bridge_subdir -eq $Identity.Bridge
        ) { return $value }
      } catch {}
    }
    Start-Sleep -Milliseconds 500
  } while ((Get-Date) -lt $deadline)
  throw "EA identity/hedging preflight failed: $Path"
}

function Enable-ExpertTrading {
  $bridgeItem = Get-Item `
    (Join-Path $env:APPDATA "MetaQuotes\Terminal\*\MQL5\Files\bridge") `
    -ErrorAction Stop | Select-Object -First 1
  $terminalData = Split-Path (Split-Path (Split-Path $bridgeItem.FullName))
  $chartsRoot = Join-Path $terminalData "MQL5\Profiles\Charts"
  $names = @("ForgeBridge", "ForgeBridgeH1")
  foreach ($name in $names) {
    $chart = Get-ChildItem $chartsRoot -Filter "*.chr" -Recurse |
      Where-Object { (Get-Content $_.FullName -Raw) -match "(?m)^name=$name\s*$" } |
      Select-Object -First 1
    if (-not $chart) { throw "Chart for $name not found." }
    $text = Get-Content $chart.FullName -Raw
    $text = [regex]::Replace(
      $text,
      "(?s)(<expert>\s*name=$name.*?expertmode=)0(.*?</expert>)",
      '${1}1${2}',
      1
    )
    Set-Content $chart.FullName $text -Encoding Unicode
  }
  $terminal = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq "terminal64.exe" -and $_.ExecutablePath -match "XM Global MT5" } |
    Select-Object -First 1
  $exe = if ($terminal) { $terminal.ExecutablePath } else { "C:\Program Files\XM Global MT5\terminal64.exe" }
  if ($terminal) { Stop-Process -Id $terminal.ProcessId -Force }
  Start-Process $exe
  Start-Sleep -Seconds 10
}

function Deploy-Dual {
  Stop-Services
  Invoke-App $M15Root Stop $M15AppPort
  Invoke-App $H1Root Stop $H1AppPort
  & powershell -ExecutionPolicy Bypass -File (Join-Path $M15Root "scripts\deploy_xm_forgebridge.ps1") `
    -Attach -SkipBridgeService -RiskPct 1.0
  if ($LASTEXITCODE -ne 0) { throw "M15 EA deploy failed." }
  & powershell -ExecutionPolicy Bypass -File (Join-Path $H1Root "scripts\deploy_xm_forgebridge.ps1") `
    -Attach -SkipBridgeService -RiskPct 1.0
  if ($LASTEXITCODE -ne 0) { throw "H1 EA deploy failed." }
  Read-Connection (Join-Path $M15Root "mt5\bridge\connection.json") $Expected.M15 | Out-Null
  Read-Connection (Join-Path $H1Root "mt5\bridge_h1\connection.json") $Expected.H1 | Out-Null
  Enable-ExpertTrading
  Start-Services
  Invoke-App $M15Root Start $M15AppPort
  Invoke-App $H1Root Start $H1AppPort
}

function Show-Status {
  $processes = Get-CimInstance Win32_Process
  foreach ($item in @(
    @{ Name = "M15 app"; Pattern = [regex]::Escape("$M15Root\gui\app.py"); Port = 8501 },
    @{ Name = "H1 app"; Pattern = [regex]::Escape("$H1Root\gui\app.py"); Port = 8502 },
    @{ Name = "M15 bridge"; Pattern = [regex]::Escape("$M15Root\mt5\bridge"); Port = 8765 },
    @{ Name = "H1 bridge"; Pattern = [regex]::Escape("$H1Root\mt5\bridge_h1"); Port = 8865 },
    @{ Name = "M15 paper"; Pattern = [regex]::Escape("$M15Root\scripts\paper_monitor_service.py"); Port = 8766 },
    @{ Name = "H1 paper"; Pattern = [regex]::Escape("$H1Root\scripts\paper_monitor_service.py"); Port = 8866 }
  )) {
    $count = @($processes | Where-Object { $_.CommandLine -match $item.Pattern }).Count
    $listener = Get-NetTCPConnection -State Listen -LocalPort $item.Port -ErrorAction SilentlyContinue
    Write-Host "$($item.Name): process=$count port=$([bool]$listener)"
  }
}

Assert-Layout
switch ($Action) {
  "Deploy" { Deploy-Dual; Show-Status }
  "Start" {
    Start-Services
    Invoke-App $M15Root Start $M15AppPort
    Invoke-App $H1Root Start $H1AppPort
    Show-Status
  }
  "Restart" {
    Stop-Services
    Invoke-App $M15Root Stop $M15AppPort
    Invoke-App $H1Root Stop $H1AppPort
    Start-Services
    Invoke-App $M15Root Start $M15AppPort
    Invoke-App $H1Root Start $H1AppPort
    Show-Status
  }
  "Stop" {
    Stop-Services
    Invoke-App $M15Root Stop $M15AppPort
    Invoke-App $H1Root Stop $H1AppPort
    Show-Status
  }
  "Status" { Show-Status }
}
