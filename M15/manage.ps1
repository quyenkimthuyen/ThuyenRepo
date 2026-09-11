# Fleet manager — start/stop/restart/status every M15 clone under this folder.
#
#   .\manage.ps1 Status
#   .\manage.ps1 Start
#   .\manage.ps1 Stop
#   .\manage.ps1 Restart
#   .\manage.ps1 Start M15_RR1
#   .\manage.ps1 Start RR2 trade
#   .\manage.ps1 Stop RR1 e21
#
[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateSet("Start", "Stop", "Restart", "Status")]
  [string]$Action = "Status",
  [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
  [string[]]$Filters = @(),
  [ValidateRange(5, 120)]
  [int]$TimeoutSeconds = 40
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Action = @{
  start = "Start"; stop = "Stop"; restart = "Restart"; status = "Status"
}[$Action.ToLowerInvariant()]
if (-not $Action) { throw "Unknown action." }

function Get-CloneDirs {
  Get-ChildItem -LiteralPath $Root -Directory |
    Where-Object {
      (Test-Path -LiteralPath (Join-Path $_.FullName "Train\manage.ps1")) -or
      (Test-Path -LiteralPath (Join-Path $_.FullName "Trade\live\scripts\run_app_windows.ps1"))
    } |
    Sort-Object Name
}

function Read-LivePort([string]$CloneRoot) {
  $path = Join-Path $CloneRoot "Trade\shared\constants.py"
  if (-not (Test-Path -LiteralPath $path)) { return $null }
  foreach ($line in Get-Content -LiteralPath $path) {
    if ($line -match '^\s*LIVE_APP_PORT\s*=\s*(\d+)') {
      return [int]$Matches[1]
    }
  }
  return $null
}

function Read-TrainDesks([string]$CloneRoot) {
  $dir = Join-Path $CloneRoot "Train\desks"
  if (-not (Test-Path -LiteralPath $dir)) { return @() }
  $rows = @()
  Get-ChildItem -LiteralPath $dir -Filter "*.yaml" | Sort-Object Name | ForEach-Object {
    $id = $null
    $port = $null
    foreach ($line in Get-Content -LiteralPath $_.FullName) {
      $trim = $line.Split("#")[0].Trim()
      if ($trim -match '^id:\s*(\S+)') { $id = $Matches[1].Trim() }
      elseif ($trim -match '^port:\s*(\d+)') { $port = [int]$Matches[1] }
    }
    if ($id -and $port) {
      $rows += [pscustomobject]@{ Id = $id; Port = $port }
    }
  }
  return $rows
}

function Clone-Matches([string]$Name, [string[]]$Want) {
  if (-not $Want -or $Want.Count -eq 0) { return $true }
  $fold = $Name.ToLowerInvariant()
  $short = $fold
  if ($short.StartsWith("m15_")) { $short = $short.Substring(4) }
  foreach ($raw in $Want) {
    $token = $raw.Trim().ToLowerInvariant()
    if (-not $token) { continue }
    if ($token -eq $fold -or $token -eq $short -or $token -eq "m15_$short") { return $true }
  }
  return $false
}

$AppAliases = @{
  all = "all"; train = "train"; trade = "trade"; live = "trade"
  e21 = "e21"; eur = "e21"; eurusd = "e21"; eur15 = "e21"
  g23 = "g23"; gbp = "g23"; gbpusd = "g23"; gbp15 = "g23"
}

$wantClones = New-Object System.Collections.Generic.List[string]
$wantApps = New-Object System.Collections.Generic.List[string]
foreach ($raw in @($Filters)) {
  foreach ($part in ($raw -split "[,\s]+" | Where-Object { $_ })) {
    $token = $part.Trim().ToLowerInvariant()
    if ($AppAliases.ContainsKey($token)) {
      $id = $AppAliases[$token]
      if (-not $wantApps.Contains($id)) { [void]$wantApps.Add($id) }
    } else {
      [void]$wantClones.Add($part.Trim())
    }
  }
}
if ($wantApps.Count -eq 0) { [void]$wantApps.Add("all") }

function App-Wanted([string]$Kind) {
  if ($wantApps.Contains("all")) { return $true }
  if ($Kind -eq "train") { return $wantApps.Contains("train") -or $wantApps.Contains("e21") -or $wantApps.Contains("g23") }
  if ($Kind -eq "trade") { return $wantApps.Contains("trade") }
  return $wantApps.Contains($Kind) -or $wantApps.Contains("train")
}

function Train-DeskArgs {
  $ids = @()
  if ($wantApps.Contains("all") -or $wantApps.Contains("train")) {
    $ids = @("e21", "g23")
  } else {
    if ($wantApps.Contains("e21")) { $ids += "e21" }
    if ($wantApps.Contains("g23")) { $ids += "g23" }
  }
  return $ids
}

function Invoke-ChildScript([string]$File, [string[]]$ArgumentList) {
  # Do not use Start-Process -Wait (waits for Streamlit children).
  # Pipe to Out-Host so child Write-Host/stdout is not captured into $code.
  $exe = Join-Path $PSHOME "powershell.exe"
  if (-not (Test-Path -LiteralPath $exe)) { $exe = "powershell.exe" }
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & $exe -NoProfile -ExecutionPolicy Bypass -File $File @ArgumentList | Out-Host
    if ($null -eq $LASTEXITCODE) { return 0 }
    return [int]$LASTEXITCODE
  } finally {
    $ErrorActionPreference = $prev
  }
}

function Test-PortUp([int]$Port) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port" -UseBasicParsing -TimeoutSec 2
    return ($r.StatusCode -eq 200)
  } catch {
    return $false
  }
}

function Show-FleetStatus {
  Write-Host ""
  Write-Host ("{0,-10} {1,-10} {2,-8} {3}" -f "CLONE", "APP", "PORT", "STATE")
  Write-Host ("{0,-10} {1,-10} {2,-8} {3}" -f "-----", "---", "----", "-----")
  foreach ($clone in $clones) {
    if (App-Wanted "train") {
      foreach ($desk in @(Read-TrainDesks $clone.FullName)) {
        if (-not (App-Wanted $desk.Id)) { continue }
        $state = if (Test-PortUp $desk.Port) { "RUNNING" } else { "STOPPED" }
        Write-Host ("{0,-10} {1,-10} {2,-8} {3}" -f $clone.Name, ("train/" + $desk.Id), $desk.Port, $state)
      }
    }
    if (App-Wanted "trade") {
      $port = Read-LivePort $clone.FullName
      if ($port) {
        $state = if (Test-PortUp $port) { "RUNNING" } else { "STOPPED" }
        Write-Host ("{0,-10} {1,-10} {2,-8} {3}" -f $clone.Name, "trade", $port, $state)
      }
    }
  }
}

$clones = @(Get-CloneDirs | Where-Object { Clone-Matches $_.Name @($wantClones) })
if ($clones.Count -eq 0) {
  throw "No M15 clones matched under $Root"
}

$failures = 0
Write-Host ("M15 fleet {0} -> {1}" -f $Action, (($clones | ForEach-Object { $_.Name }) -join ", ")) -ForegroundColor Cyan

if ($Action -eq "Status") {
  Show-FleetStatus
  Write-Host ""
  Write-Host "Done." -ForegroundColor Green
  exit 0
}

foreach ($clone in $clones) {
  $name = $clone.Name
  $trainManage = Join-Path $clone.FullName "Train\manage.ps1"
  $tradeRun = Join-Path $clone.FullName "Trade\live\scripts\run_app_windows.ps1"

  if ((Test-Path -LiteralPath $trainManage) -and (App-Wanted "train")) {
    $deskArgs = @(Train-DeskArgs)
    if ($deskArgs.Count -gt 0) {
      $deskPorts = @()
      foreach ($d in @(Read-TrainDesks $clone.FullName)) {
        if ($deskArgs -contains $d.Id) { $deskPorts += ("{0}:{1}" -f $d.Id, $d.Port) }
      }
      Write-Host ""
      Write-Host ("==== {0} train ({1}) ====" -f $name, ($deskPorts -join ", ")) -ForegroundColor Yellow
      $code = Invoke-ChildScript $trainManage @($Action, ($deskArgs -join ","), "-TimeoutSeconds", "$TimeoutSeconds")
      if ($code -ne 0) { $failures++ }
    }
  }

  if ((Test-Path -LiteralPath $tradeRun) -and (App-Wanted "trade")) {
    $port = Read-LivePort $clone.FullName
    if (-not $port) { $port = 8501 }
    Write-Host ""
    Write-Host ("==== {0} trade (:{1}) ====" -f $name, $port) -ForegroundColor Yellow
    $code = Invoke-ChildScript $tradeRun @("-Action", $Action, "-Port", "$port", "-TimeoutSeconds", "$TimeoutSeconds")
    if ($code -ne 0) { $failures++ }
  }
}

Write-Host ""
if ($failures -gt 0) {
  Write-Host ("Done with {0} failure(s)." -f $failures) -ForegroundColor Red
  exit 1
}
Write-Host "Done." -ForegroundColor Green
