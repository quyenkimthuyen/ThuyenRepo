param(
  [ValidateSet("start", "stop", "restart", "status")]
  [string]$Action = "start",

  [int]$Port = 8501,

  [switch]$Install
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$App = Join-Path $Root "gui\app.py"
$PidFile = Join-Path $Root ".streamlit-app.pid"
$LogDir = Join-Path $Root "logs"
$StdoutLog = Join-Path $LogDir "streamlit.out.log"
$StderrLog = Join-Path $LogDir "streamlit.err.log"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

function Get-AppProcess {
  if (-not (Test-Path $PidFile)) {
    return $null
  }

  $processId = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
  if (-not $processId) {
    return $null
  }

  return Get-Process -Id ([int]$processId) -ErrorAction SilentlyContinue
}

function Get-Python {
  if (Test-Path $VenvPython) {
    return $VenvPython
  }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    return $python.Source
  }

  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    return $py.Source
  }

  throw "Python was not found. Install Python 3 or add it to PATH."
}

function Quote-Arg([string]$Value) {
  return '"' + ($Value -replace '"', '\"') + '"'
}

function Install-Dependencies {
  if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment..."
    $basePython = Get-Python
    & $basePython -m venv (Join-Path $Root ".venv")
  }

  Write-Host "Installing dependencies..."
  & $VenvPython -m pip install --upgrade pip
  & $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")
}

function Start-App {
  $existing = Get-AppProcess
  if ($existing) {
    Write-Host "App is already running on PID $($existing.Id)."
    return
  }

  if ($Install) {
    Install-Dependencies
  }

  if (-not (Test-Path $App)) {
    throw "Streamlit app was not found at $App"
  }

  if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
  }

  $python = Get-Python
  $env:PYTHONUTF8 = "1"
  $env:PYTHONIOENCODING = "utf-8"
  $arguments = @(
    "-m",
    "streamlit",
    "run",
    (Quote-Arg $App),
    "--server.headless",
    "true",
    "--server.port",
    "$Port",
    "--browser.gatherUsageStats",
    "false"
  ) -join " "

  $process = Start-Process `
    -FilePath $python `
    -ArgumentList $arguments `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog `
    -PassThru `
    -WindowStyle Minimized

  Set-Content -Path $PidFile -Value $process.Id
  Write-Host "Started app on PID $($process.Id)."
  Write-Host "Open: http://localhost:$Port"
  Write-Host "Logs: $StdoutLog"
}

function Stop-App {
  $existing = Get-AppProcess
  if (-not $existing) {
    if (Test-Path $PidFile) {
      Remove-Item $PidFile -Force
    }
    Write-Host "App is not running."
    return
  }

  Stop-Process -Id $existing.Id -Force
  Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
  Write-Host "Stopped app on PID $($existing.Id)."
}

function Show-Status {
  $existing = Get-AppProcess
  if ($existing) {
    Write-Host "App is running on PID $($existing.Id)."
    Write-Host "Open: http://localhost:$Port"
  } else {
    Write-Host "App is not running."
  }
}

switch ($Action) {
  "start" { Start-App }
  "stop" { Stop-App }
  "restart" {
    Stop-App
    Start-App
  }
  "status" { Show-Status }
}
