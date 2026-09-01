# After Windows logon: start XM MT5, this desk's Streamlit app, then Live Bridge worker.
# Registered per-desk when Live Trade / Bridge Start; removed on Stop.
#
# Keep this file ASCII-only. Windows PowerShell 5.1 (scheduled tasks) reads
# BOM-less UTF-8 as ANSI; a Unicode dash then breaks parsing and the task
# exits 1 with no log.
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$Desk,
  [string]$Python = ""
)

$ErrorActionPreference = "Continue"
$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Desk = "$Desk".Trim().ToLowerInvariant()
$LogDir = Join-Path $AppRoot "runtime\$Desk\results"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir "live_windows_boot.log"

function Write-Boot([string]$Message) {
  $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ss"), $Message
  Add-Content -LiteralPath $Log -Value $line -ErrorAction SilentlyContinue
  Write-Host $line
}

function Resolve-Python([string]$Hint) {
  if ($Hint -and (Test-Path -LiteralPath $Hint)) { return $Hint }
  foreach ($c in @("python", "py")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
  }
  throw "Python not found"
}

function Find-XmTerminalExe {
  $running = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -eq "terminal64.exe" -and
      $_.ExecutablePath -and
      $_.ExecutablePath -match "XM Global MT5"
    } |
    Select-Object -First 1
  if ($running -and $running.ExecutablePath) {
    return $running.ExecutablePath
  }
  foreach ($dir in @(
    "C:\Program Files\XM Global MT5",
    "C:\Program Files (x86)\XM Global MT5"
  )) {
    $exe = Join-Path $dir "terminal64.exe"
    if (Test-Path -LiteralPath $exe) { return $exe }
  }
  return $null
}

function Start-XmMt5IfNeeded {
  $existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -eq "terminal64.exe" -and
      $_.ExecutablePath -and
      $_.ExecutablePath -match "XM Global MT5"
    }
  if ($existing) {
    Write-Boot ("MT5 already running PID {0}" -f $existing[0].ProcessId)
    return
  }
  $exe = Find-XmTerminalExe
  if (-not $exe) {
    Write-Boot "XM Global MT5 not found - start terminal manually."
    return
  }
  Write-Boot "Starting MT5 $exe"
  Start-Process -FilePath $exe
  $deadline = (Get-Date).AddSeconds(45)
  while ((Get-Date) -lt $deadline) {
    $hit = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
      Where-Object {
        $_.Name -eq "terminal64.exe" -and
        $_.ExecutablePath -and
        $_.ExecutablePath -match "XM Global MT5"
      }
    if ($hit) {
      Write-Boot ("MT5 online PID {0}" -f $hit[0].ProcessId)
      Start-Sleep -Seconds 12
      return
    }
    Start-Sleep -Seconds 2
  }
  Write-Boot "MT5 start timed out"
}

Write-Boot "boot begin desk=$Desk"
try {
  Start-XmMt5IfNeeded
} catch {
  Write-Boot ("MT5 start error: {0}" -f $_.Exception.Message)
}

$manage = Join-Path $AppRoot "manage.ps1"
if (Test-Path -LiteralPath $manage) {
  Write-Boot "Starting desk app via manage.ps1 Start $Desk"
  try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $manage Start $Desk
    Write-Boot "manage.ps1 Start done (exit $LASTEXITCODE)"
  } catch {
    Write-Boot ("manage.ps1 Start error: {0}" -f $_.Exception.Message)
  }
} else {
  Write-Boot "manage.ps1 missing: $manage"
}

try {
  $py = Resolve-Python $Python
  $resume = Join-Path $AppRoot "scripts\resume_live_worker.py"
  Write-Boot "Resume worker $py $resume --desk $Desk"
  $env:TRAINAPP_ROOT = $AppRoot
  $env:TRAINAPP_DESK = $Desk
  $prevPy = $env:PYTHONPATH
  $corePath = Join-Path $AppRoot "cores\m15"
  $env:PYTHONPATH = ($AppRoot + ";" + $corePath)
  if ($prevPy) { $env:PYTHONPATH = $env:PYTHONPATH + ";" + $prevPy }
  & $py -u $resume --desk $Desk
  Write-Boot "resume_live_worker exit $LASTEXITCODE"
} catch {
  Write-Boot ("worker resume error: {0}" -f $_.Exception.Message)
}

Write-Boot "boot end"
exit 0
