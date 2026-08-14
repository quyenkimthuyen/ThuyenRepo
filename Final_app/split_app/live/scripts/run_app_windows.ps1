[CmdletBinding()]
param(
  [ValidateSet("Start", "Restart", "Stop", "Status")]
  [string]$Action = "Restart",
  [ValidateRange(1, 65535)]
  [int]$Port = 8601,
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
      $_.CommandLine -match "streamlit" -and
      $_.CommandLine -match $escapedAppPath
    } |
    ForEach-Object { [void]$processIds.Add([int]$_.ProcessId) }

  Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
    ForEach-Object {
      $row = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)" -ErrorAction SilentlyContinue
      if ($row -and $row.CommandLine -match "streamlit" -and $row.CommandLine -match $escapedAppPath) {
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

function Get-PortListeners {
  @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Clear-PortIfStale {
  $listeners = @(Get-PortListeners)
  if ($listeners.Count -eq 0) {
    return
  }

  foreach ($row in $listeners) {
    $ownerId = [int]$row.OwningProcess
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$ownerId" -ErrorAction SilentlyContinue
    if (-not $proc) {
      Write-Host "Port $Port lists dead PID $ownerId (ghost) - ignoring stale table entry."
      continue
    }

    $cmd = [string]$proc.CommandLine
    $isOurs = ($cmd -match "streamlit") -and ($cmd -match [regex]::Escape($AppPath))
    $healthy = Test-AppHealth
    if ($isOurs -or -not $healthy) {
      Write-Host "Reclaiming port $Port from PID $ownerId..."
      Stop-Process -Id $ownerId -Force -ErrorAction SilentlyContinue
      try { taskkill /F /PID $ownerId 2>$null | Out-Null } catch {}
    }
    else {
      throw "Port $Port is already used by PID $ownerId ($($proc.Name))."
    }
  }

  $deadline = (Get-Date).AddSeconds(8)
  while ((Get-Date) -lt $deadline) {
    $left = @(Get-PortListeners | Where-Object {
      $null -ne (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue)
    })
    if ($left.Count -eq 0) {
      return
    }
    Start-Sleep -Milliseconds 250
  }

  # Ghost Listen rows (PID gone) still block some Windows builds - try bind probe via Start.
  $alive = @(Get-PortListeners | Where-Object {
    $null -ne (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue)
  })
  if ($alive.Count -gt 0) {
    throw "Port $Port still held by PID $($alive[0].OwningProcess)."
  }
  Write-Host "Port $Port free of live owners (stale netstat rows may remain)."
}

function Stop-App {
  $rows = @(Get-AppProcesses)
  foreach ($row in $rows) {
    Write-Host "Stopping app PID $($row.ProcessId)..."
    Stop-Process -Id $row.ProcessId -Force -ErrorAction SilentlyContinue
  }

  # Also stop anything still listening on our port (orphaned pythonw / ghost reclaim).
  foreach ($listener in @(Get-PortListeners)) {
    $ownerId = [int]$listener.OwningProcess
    if ($ownerId -le 0) { continue }
    $proc = Get-Process -Id $ownerId -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host "Stopping port owner PID $ownerId..."
      Stop-Process -Id $ownerId -Force -ErrorAction SilentlyContinue
    }
  }

  Remove-Item $PidFile -Force -ErrorAction SilentlyContinue

  $deadline = (Get-Date).AddSeconds(10)
  while ((Get-Date) -lt $deadline) {
    $aliveApps = @(Get-AppProcesses)
    $alivePort = @(Get-PortListeners | Where-Object {
      $null -ne (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue)
    })
    if (($aliveApps.Count -eq 0) -and ($alivePort.Count -eq 0)) {
      break
    }
    Start-Sleep -Milliseconds 250
  }
  Write-Host "App stopped."
}

function Test-PortHasLiveOwner {
  param([int]$CheckPort)
  foreach ($row in @(Get-NetTCPConnection -State Listen -LocalPort $CheckPort -ErrorAction SilentlyContinue)) {
    if (Get-Process -Id $row.OwningProcess -ErrorAction SilentlyContinue) {
      return $true
    }
  }
  return $false
}

function Test-PortHttpOk {
  param([int]$CheckPort)
  try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:$CheckPort" -UseBasicParsing -TimeoutSec 3
    return $response.StatusCode -eq 200
  }
  catch {
    return $false
  }
}

function Find-FreeAppPort {
  param([int]$Preferred)
  $candidates = @($Preferred)
  foreach ($p in 8601, 8602, 8603, 8604, 8605) {
    if ($p -ne $Preferred) { $candidates += $p }
  }
  foreach ($p in $candidates) {
    if (-not (Test-PortHasLiveOwner -CheckPort $p)) {
      # Ghost-only listen still breaks HTTP on some Windows builds — skip if HTTP already dead-locked.
      if ((Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue) -and -not (Test-PortHttpOk -CheckPort $p)) {
        # Only ghosts: try next port
        $live = $false
        foreach ($row in @(Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue)) {
          if (Get-Process -Id $row.OwningProcess -ErrorAction SilentlyContinue) { $live = $true }
        }
        if (-not $live) {
          Write-Host "Port $p has ghost listener (dead PID) - trying next port."
          continue
        }
      }
      return $p
    }
  }
  return $Preferred
}

function Start-App {
  $running = @(Get-AppProcesses)
  if ($running.Count -gt 0 -and (Test-AppHealth)) {
    Write-Host "App is already running: $AppUrl (PID $($running[0].ProcessId))"
    return
  }

  Clear-PortIfStale

  $script:Port = Find-FreeAppPort -Preferred $Port
  $script:AppUrl = "http://127.0.0.1:$Port"
  if ($Port -ne 8601) {
    Write-Host "Using fallback port $Port (8601 blocked by stale/ghost socket)."
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
  Write-Host "Starting app PID $($created.ProcessId) on port $Port..."

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-PortHttpOk -CheckPort $Port) {
      Write-Host "App ready: $AppUrl"
      return
    }
    if (-not (Get-Process -Id $created.ProcessId -ErrorAction SilentlyContinue)) {
      throw "App process exited during startup."
    }
    Start-Sleep -Seconds 1
  }

  # Timed out — usually ghost socket ate the bind. Kill and retry one fallback port.
  Write-Host "Port $Port did not become healthy — stopping PID $($created.ProcessId) and retrying fallback."
  Stop-Process -Id $created.ProcessId -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1

  $fallback = 8602
  if ($Port -eq 8602) { $fallback = 8603 }
  if (Test-PortHasLiveOwner -CheckPort $fallback) {
    throw "App did not become ready on $Port within $TimeoutSeconds seconds (fallback $fallback also busy)."
  }
  $script:Port = $fallback
  $script:AppUrl = "http://127.0.0.1:$Port"
  $commandLine = (
    "`"$pythonw`" -m streamlit run `"$AppPath`" " +
    "--server.port $Port --server.headless true " +
    "--browser.gatherUsageStats false --server.fileWatcherType none"
  )
  $created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create `
    -Arguments @{ CommandLine = $commandLine; CurrentDirectory = $RepoRoot }
  if ($created.ReturnValue -ne 0) {
    throw "Cannot start fallback app (Win32 return=$($created.ReturnValue))."
  }
  Set-Content -Path $PidFile -Value $created.ProcessId -Encoding ascii
  Write-Host "Starting fallback app PID $($created.ProcessId) on port $Port..."
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-PortHttpOk -CheckPort $Port) {
      Write-Host "App ready: $AppUrl"
      return
    }
    if (-not (Get-Process -Id $created.ProcessId -ErrorAction SilentlyContinue)) {
      throw "Fallback app process exited during startup."
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
