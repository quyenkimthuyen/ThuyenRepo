# TrainApp manager — unified Train desks (E21/G23/E31/G33).
#
#   .\manage.ps1 Start
#   .\manage.ps1 Start e21,g23
#   .\manage.ps1 Stop
#   .\manage.ps1 Restart e31
#   .\manage.ps1 Status
#   .\manage.ps1 Check
#
[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateSet("Start", "Stop", "Restart", "Status", "Check")]
  [string]$Action = "Status",
  [Parameter(Position = 1)]
  [Alias("App")]
  [string[]]$Apps = @("e21", "g23", "e31", "g33"),
  [ValidateRange(5, 120)]
  [int]$TimeoutSeconds = 40
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Python = $null
foreach ($c in @("python", "py")) {
  $cmd = Get-Command $c -ErrorAction SilentlyContinue
  if ($cmd) { $Python = $cmd.Source; break }
}
if (-not $Python) { throw "Python not found on PATH" }

$Catalog = [ordered]@{
  e21 = @{ Port = 8711; Label = "E21" }
  g23 = @{ Port = 8731; Label = "G23" }
  e31 = @{ Port = 8811; Label = "E31" }
  g33 = @{ Port = 8831; Label = "G33" }
}

function Resolve-DeskIds([string[]]$Requested) {
  $keys = [System.Collections.Generic.List[string]]::new()
  foreach ($raw in $Requested) {
    foreach ($part in ($raw -split "[,\s]+" | Where-Object { $_ })) {
      $token = $part.Trim().ToLowerInvariant()
      if ($token -eq "all") {
        foreach ($k in $Catalog.Keys) { if (-not $keys.Contains($k)) { [void]$keys.Add($k) } }
        continue
      }
      $map = @{
        e21 = "e21"; eur15 = "e21"; eurm15 = "e21"; m15e21 = "e21"
        g23 = "g23"; gbp15 = "g23"; gbpm15 = "g23"; m15g23 = "g23"
        e31 = "e31"; eur5 = "e31"; eurm5 = "e31"; m5e31 = "e31"
        g33 = "g33"; gbp5 = "g33"; gbpm5 = "g33"; m5g33 = "g33"
      }
      if ($token -eq "gbp" -or $token -eq "gbpusd") {
        throw "Alias '$part' is ambiguous (G23=M15 vs G33=M5). Use g23 or g33 (or gbp15 / gbp5)."
      }
      if ($token -eq "eur" -or $token -eq "eurusd") {
        throw "Alias '$part' is ambiguous (E21=M15 vs E31=M5). Use e21 or e31 (or eur15 / eur5)."
      }
      if ($Catalog.Contains($token)) { $id = $token }
      elseif ($map.ContainsKey($token)) { $id = $map[$token] }
      else { throw "Unknown desk '$part'. Use e21 g23 e31 g33 or All." }
      if (-not $keys.Contains($id)) { [void]$keys.Add($id) }
    }
  }
  if ($keys.Count -eq 0) { throw "No desks selected." }
  return ,$keys.ToArray()
}

function Get-DeskProcesses([string]$DeskId, [int]$Port) {
  $rows = @()
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.CommandLine -and
      $_.CommandLine -match "streamlit" -and
      (
        $_.CommandLine -match [regex]::Escape("TrainApp") -or
        $_.CommandLine -match "run_desk" -or
        $_.CommandLine -match [regex]::Escape("LiveCheck\Train\") -or
        $_.CommandLine -match [regex]::Escape("LiveCheck/Train/")
      ) -and
      (
        $_.CommandLine -match "--server.port $Port" -or
        $_.CommandLine -match "server.port=$Port"
      )
    } |
    ForEach-Object { $rows += $_ }

  Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
    ForEach-Object {
      $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)" -ErrorAction SilentlyContinue
      if ($proc -and $proc.CommandLine -match "streamlit") { $rows += $proc }
    }
  $rows | Sort-Object ProcessId -Unique
}

function Test-IsTrainAppProcess($Proc) {
  if (-not $Proc -or -not $Proc.CommandLine) { return $false }
  return (
    $Proc.CommandLine -match [regex]::Escape("TrainApp") -or
    $Proc.CommandLine -match "run_desk"
  )
}

function Stop-Desk([string]$DeskId) {
  $port = [int]$Catalog[$DeskId].Port
  $rows = @(Get-DeskProcesses -DeskId $DeskId -Port $port)
  foreach ($row in $rows) {
    Write-Host "Stopping $($Catalog[$DeskId].Label) PID $($row.ProcessId)..."
    Stop-Process -Id $row.ProcessId -Force -ErrorAction SilentlyContinue
  }
  $pidFile = Join-Path $Root "runtime\$DeskId\results\streamlit_app.pid"
  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
  Write-Host "Stopped $($Catalog[$DeskId].Label) (:$port)"
}

function Start-Desk([string]$DeskId) {
  $port = [int]$Catalog[$DeskId].Port
  $label = $Catalog[$DeskId].Label
  $existing = @(Get-DeskProcesses -DeskId $DeskId -Port $port)
  $trainApp = @($existing | Where-Object { Test-IsTrainAppProcess $_ })
  if ($trainApp.Count -gt 0) {
    Write-Host "Already running $($label) PID $($trainApp[0].ProcessId) http://127.0.0.1:$port"
    return
  }
  if ($existing.Count -gt 0) {
    Write-Host "Releasing port $port from old Train desk..."
    foreach ($row in $existing) {
      Stop-Process -Id $row.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
  }
  Write-Host ("==== {0} ({1}) port {2} - Start ====" -f $label, $DeskId, $port) -ForegroundColor Cyan
  $env:TRAINAPP_DESK = $DeskId
  $argList = @(
    (Join-Path $Root "run_desk.py"), $DeskId, "--port", "$port"
  )
  $proc = Start-Process -FilePath $Python -ArgumentList $argList -WorkingDirectory $Root -WindowStyle Hidden -PassThru
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  $ready = $false
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -Uri "http://127.0.0.1:$port" -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 500
  }
  if ($ready) {
    Write-Host "App ready: http://127.0.0.1:$port (PID $($proc.Id))"
  } else {
    Write-Host "Started PID $($proc.Id) but health check timed out - open http://127.0.0.1:$port" -ForegroundColor Yellow
  }
}

function Show-Status([string]$DeskId) {
  $port = [int]$Catalog[$DeskId].Port
  $rows = @(Get-DeskProcesses -DeskId $DeskId -Port $port)
  $trainApp = @($rows | Where-Object { Test-IsTrainAppProcess $_ })
  if ($trainApp.Count -gt 0) {
    Write-Host ("{0} (:{1}) RUNNING TrainApp PID {2}" -f $Catalog[$DeskId].Label, $port, $trainApp[0].ProcessId)
  } elseif ($rows.Count -gt 0) {
    Write-Host ("{0} (:{1}) RUNNING old-Train PID {2}" -f $Catalog[$DeskId].Label, $port, $rows[0].ProcessId)
  } else {
    Write-Host ("{0} (:{1}) STOPPED" -f $Catalog[$DeskId].Label, $port)
  }
}

$selected = Resolve-DeskIds $Apps
Write-Host ("TrainApp manage: {0} -> {1}" -f $Action, ($selected -join ", "))

foreach ($id in $selected) {
  switch ($Action) {
    "Start" { Start-Desk $id }
    "Stop" { Stop-Desk $id }
    "Restart" { Stop-Desk $id; Start-Sleep -Seconds 1; Start-Desk $id }
    "Status" { Show-Status $id }
    "Check" {
      & $Python (Join-Path $Root "run_desk.py") $id --check
      if ($LASTEXITCODE -ne 0) { throw "Check failed for $id" }
    }
  }
}
Write-Host ""
Write-Host "Done." -ForegroundColor Green
