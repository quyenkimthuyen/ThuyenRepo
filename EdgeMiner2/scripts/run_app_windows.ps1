[CmdletBinding()]
param(
  [ValidateSet("Start", "Restart", "Stop", "Status")]
  [string]$Action = "Restart",
  [ValidateRange(1, 65535)]
  [int]$Port = 8501,
  [ValidateRange(5, 120)]
  [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AppPath = Join-Path $RepoRoot "gui\app.py"
$PidFile = Join-Path $RepoRoot "results\streamlit_app.pid"
$AppUrl = "http://127.0.0.1:$Port"

function Test-AppHealth {
  try {
    $response = Invoke-WebRequest -Uri $AppUrl -UseBasicParsing -TimeoutSec 3
    return $response.StatusCode -eq 200
  }
  catch {
    return $false
  }
}

function Get-AppProcesses {
  $processIds = [System.Collections.Generic.HashSet[int]]::new()
  $escapedAppPath = [regex]::Escape($AppPath)

  if (Test-Path $PidFile) {
    $savedId = 0
    [void][int]::TryParse((Get-Content $PidFile -Raw).Trim(), [ref]$savedId)
    if ($savedId -gt 0) {
      [void]$processIds.Add($savedId)
    }
  }

  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.CommandLine -match "streamlit" -and (
        $_.CommandLine -match $escapedAppPath -or
        $_.CommandLine -match "gui[/\\]app\.py"
      )
    } |
    ForEach-Object { [void]$processIds.Add([int]$_.ProcessId) }

  Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
    ForEach-Object {
      $row = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)" -ErrorAction SilentlyContinue
      if ($row -and $row.CommandLine -match "streamlit" -and $row.CommandLine -match "gui[/\\]app\.py") {
        [void]$processIds.Add([int]$row.ProcessId)
      }
    }

  foreach ($processId in $processIds) {
    $row = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
    if ($row -and $row.CommandLine -match "streamlit") {
      $row
    }
  }
}

function Stop-App {
  $rows = @(Get-AppProcesses)
  foreach ($row in $rows) {
    Write-Host "Stopping app PID $($row.ProcessId)..."
    Stop-Process -Id $row.ProcessId -Force -ErrorAction SilentlyContinue
  }
  Remove-Item $PidFile -Force -ErrorAction SilentlyContinue

  $deadline = (Get-Date).AddSeconds(10)
  while ((Get-AppProcesses) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 250
  }
  Write-Host "App stopped."
}

function Start-App {
  $running = @(Get-AppProcesses)
  if ($running.Count -gt 0 -and (Test-AppHealth)) {
    Write-Host "App is already running: $AppUrl (PID $($running[0].ProcessId))"
    return
  }

  $portOwner = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($portOwner) {
    throw "Port $Port is already used by PID $($portOwner.OwningProcess)."
  }

  $python = (Get-Command python -ErrorAction Stop).Source
  $pythonw = Join-Path (Split-Path $python) "pythonw.exe"
  if (-not (Test-Path $pythonw)) {
    $pythonw = $python
  }

  $commandLine = (
    "`"$pythonw`" -m streamlit run `"$AppPath`" " +
    "--server.port $Port --server.headless true " +
    "--browser.gatherUsageStats false --server.fileWatcherType none"
  )
  $created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create `
    -Arguments @{ CommandLine = $commandLine; CurrentDirectory = $RepoRoot }
  if ($created.ReturnValue -ne 0) {
    throw "Cannot start app (Win32 return=$($created.ReturnValue))."
  }

  New-Item -ItemType Directory -Path (Split-Path $PidFile) -Force | Out-Null
  Set-Content -Path $PidFile -Value $created.ProcessId -Encoding ascii
  Write-Host "Starting app PID $($created.ProcessId)..."

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-AppHealth) {
      Write-Host "App ready: $AppUrl"
      return
    }
    if (-not (Get-Process -Id $created.ProcessId -ErrorAction SilentlyContinue)) {
      throw "App process exited during startup."
    }
    Start-Sleep -Seconds 1
  }
  throw "App did not become ready within $TimeoutSeconds seconds."
}

switch ($Action) {
  "Start" {
    Start-App
  }
  "Restart" {
    Stop-App
    Start-App
  }
  "Stop" {
    Stop-App
  }
  "Status" {
    $rows = @(Get-AppProcesses)
    if ($rows.Count -gt 0 -and (Test-AppHealth)) {
      Write-Host "RUNNING: $AppUrl (PID $($rows[0].ProcessId))"
    }
    else {
      Write-Host "STOPPED"
      exit 1
    }
  }
}
