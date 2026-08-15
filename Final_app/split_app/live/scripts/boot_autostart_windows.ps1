# Boot sequence after Windows logon: XM MT5 -> Live Streamlit app -> optional bridge.
# Invoked by Scheduled Task "EdgeMinerLiveBoot" (see install_autostart_windows.ps1).
#
# IMPORTANT: Keep this file ASCII-only (or UTF-8 WITH BOM). Windows PowerShell 5.1
# reads BOM-less UTF-8 as system ANSI; UTF-8 em-dash bytes then become a stray
# quote and break parsing (functions after Start-XmMt5 disappear).
#
#   powershell -ExecutionPolicy Bypass -File .\boot_autostart_windows.ps1
#
[CmdletBinding()]
param(
  [int]$DelaySec = -1,
  [int]$Port = -1,
  [switch]$SkipMt5,
  [switch]$SkipApp,
  [switch]$StartBridge,
  [switch]$NoStartBridge
)

$ErrorActionPreference = "Stop"
$LiveRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PrefsPath = Join-Path $LiveRoot "results\autostart_prefs.json"
$LogDir = Join-Path $LiveRoot "results\debug_logs"
$RunApp = Join-Path $PSScriptRoot "run_app_windows.ps1"
$BootLog = Join-Path $LogDir ("boot_{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

function Write-BootLog([string]$Message) {
  $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ss"), $Message
  Write-Host $line
  try {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Add-Content -Path $BootLog -Value $line -Encoding utf8
  } catch {}
}

function Get-Prefs {
  $defaults = @{
    enabled = $true
    start_mt5 = $true
    start_app = $true
    start_bridge = $false
    delay_sec = 45
    port = 8601
  }
  if (-not (Test-Path $PrefsPath)) { return $defaults }
  try {
    $raw = Get-Content $PrefsPath -Raw | ConvertFrom-Json
    foreach ($k in @($defaults.Keys)) {
      if ($null -ne $raw.$k) { $defaults[$k] = $raw.$k }
    }
  } catch {}
  return $defaults
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
  $candidates = @(
    "${env:ProgramFiles}\XM Global MT5",
    "${env:ProgramFiles(x86)}\XM Global MT5"
  )
  foreach ($c in $candidates) {
    if ($c -and (Test-Path (Join-Path $c "terminal64.exe"))) {
      return $c
    }
  }
  return $null
}

function Start-XmMt5 {
  $existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "terminal64.exe" -and $_.ExecutablePath -match "XM Global MT5" }
  if (@($existing).Count -gt 0) {
    Write-BootLog ("MT5 already running PID={0}" -f $existing[0].ProcessId)
    return $true
  }
  $install = Find-XmInstallPath
  if (-not $install) {
    Write-BootLog "MT5 install not found - skip"
    return $false
  }
  $exe = Join-Path $install "terminal64.exe"
  Write-BootLog ("Starting MT5: {0}" -f $exe)
  Start-Process -FilePath $exe
  Start-Sleep -Seconds 12
  return $true
}

function Start-LiveApp([int]$AppPort) {
  if (-not (Test-Path $RunApp)) {
    throw ("Missing {0}" -f $RunApp)
  }
  Write-BootLog ("Starting Live app on :{0}" -f $AppPort)
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $RunApp -Action Start -Port $AppPort -TimeoutSeconds 60
  if ($LASTEXITCODE -ne 0) {
    throw ("run_app_windows.ps1 failed exit={0}" -f $LASTEXITCODE)
  }
}

function Resolve-LivePython {
  $candidates = @(
    "C:\Work\ThuyenRepo\EdgeMinerM15B5\.venv\Scripts\python.exe",
    (Join-Path $LiveRoot "..\..\..\EdgeMinerM15B5\.venv\Scripts\python.exe"),
    "C:\Python314\python.exe",
    "C:\Python313\python.exe",
    "C:\Python312\python.exe"
  )
  foreach ($c in $candidates) {
    if ($c -and (Test-Path -LiteralPath $c)) {
      return [string](Resolve-Path -LiteralPath $c).Path
    }
  }
  $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($cmd -and $cmd.Source -and (Test-Path -LiteralPath $cmd.Source)) {
    return [string]$cmd.Source
  }
  $cmd = Get-Command py.exe -ErrorAction SilentlyContinue
  if ($cmd -and $cmd.Source) {
    return [string]$cmd.Source
  }
  return $null
}

function Start-LiveBridgeIfRequested {
  $py = Resolve-LivePython
  if (-not $py) {
    Write-BootLog "Python not found - skip bridge start"
    return
  }
  Write-BootLog ("Starting Live bridge workers via {0}" -f $py)
  Push-Location $LiveRoot
  try {
    $env:LIVE_SKIP_EA_DEPLOY = "0"
    $code = "import bridge_control; print(bridge_control.start_bridge(auto_deploy_ea=True))"
    & $py -c $code
    if ($LASTEXITCODE -ne 0) {
      Write-BootLog ("bridge start failed exit={0}" -f $LASTEXITCODE)
    } else {
      Write-BootLog "bridge start OK"
    }
  } catch {
    Write-BootLog ("bridge start error: {0}" -f $_.Exception.Message)
  } finally {
    Pop-Location
  }
}

# --- main ---
$prefs = Get-Prefs
if ($DelaySec -lt 0) { $DelaySec = [int]$prefs.delay_sec }
if ($Port -lt 0) { $Port = [int]$prefs.port }

$doMt5 = [bool]$prefs.start_mt5
$doApp = [bool]$prefs.start_app
$doBridge = [bool]$prefs.start_bridge
if ($SkipMt5) { $doMt5 = $false }
if ($SkipApp) { $doApp = $false }
if ($StartBridge) { $doBridge = $true }
if ($NoStartBridge) { $doBridge = $false }

Write-BootLog ("Boot autostart begin delay={0}s mt5={1} app={2} bridge={3} port={4}" -f `
  $DelaySec, $doMt5, $doApp, $doBridge, $Port)

if ($DelaySec -gt 0) {
  Write-BootLog ("Waiting {0}s for desktop/network..." -f $DelaySec)
  Start-Sleep -Seconds $DelaySec
}

$failed = $false
try {
  if ($doMt5) {
    [void](Start-XmMt5)
  }
} catch {
  $failed = $true
  Write-BootLog ("MT5 step FAILED: {0}" -f $_.Exception.Message)
}

try {
  if ($doApp) {
    Start-LiveApp $Port
  }
} catch {
  $failed = $true
  Write-BootLog ("App step FAILED: {0}" -f $_.Exception.Message)
}

try {
  if ($doBridge) {
    Start-LiveBridgeIfRequested
  }
} catch {
  $failed = $true
  Write-BootLog ("Bridge step FAILED: {0}" -f $_.Exception.Message)
}

if ($failed) {
  Write-BootLog "Boot autostart finished with errors"
  exit 1
}
Write-BootLog "Boot autostart done"
exit 0
