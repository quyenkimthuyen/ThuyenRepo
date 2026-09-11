# Install / uninstall Windows logon Scheduled Task for Live boot autostart.
#
#   .\install_autostart_windows.ps1 -Action Install
#   .\install_autostart_windows.ps1 -Action Uninstall
#   .\install_autostart_windows.ps1 -Action Status
#   .\install_autostart_windows.ps1 -Action Ensure
#
# Task name is per-clone (folder + path hash) so a copied tree does not steal
# another copy's Scheduled Task. Pass -TaskName to match Python.
#
[CmdletBinding()]
param(
  [ValidateSet("Install", "Uninstall", "Status", "Ensure")]
  [string]$Action = "Status",
  [int]$DelaySec = 45,
  [int]$Port = 9501,
  [string]$TaskName = ""
)

$ErrorActionPreference = "Stop"
$LegacyTaskName = "EdgeMinerLive2Boot"
$BootScript = Join-Path $PSScriptRoot "boot_autostart_windows.ps1"
$LiveRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$CloneRoot = (Resolve-Path (Join-Path $LiveRoot "..\..")).Path

function Get-CloneTaskSuffix([string]$Root) {
  $resolved = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
  $folder = (Split-Path $resolved -Leaf) -replace '[^A-Za-z0-9._-]', '_'
  if (-not $folder) { $folder = "app" }
  $norm = $resolved.Replace('\', '/').ToLowerInvariant()
  $sha = [System.BitConverter]::ToString(
    [System.Security.Cryptography.SHA1]::Create().ComputeHash(
      [Text.Encoding]::UTF8.GetBytes($norm)
    )
  ).Replace("-", "").Substring(0, 8).ToLowerInvariant()
  return "$folder-$sha"
}

if (-not $TaskName) {
  $TaskName = "EdgeMinerLive2Boot-$(Get-CloneTaskSuffix $CloneRoot)"
}

if (-not (Test-Path $BootScript)) {
  throw "Missing boot script: $BootScript"
}

$BootScript = (Resolve-Path -LiteralPath $BootScript).Path

function Get-NamedTask([string]$Name) {
  return Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
}

function Get-TaskBootPath($task) {
  if (-not $task) { return "" }
  $joined = @($task.Actions | ForEach-Object { $_.Arguments }) -join " "
  if ($joined -match '-File\s+"([^"]+)"') { return $Matches[1] }
  if ($joined -match '-File\s+(\S+)') { return $Matches[1] }
  return ""
}

function Test-TaskPointsHere($task) {
  $cur = Get-TaskBootPath $task
  if (-not $cur) { return $false }
  try {
    $resolved = (Resolve-Path -LiteralPath $cur -ErrorAction Stop).Path
    return ($resolved -ieq $BootScript)
  } catch {
    return $false
  }
}

function Remove-StaleNamedTask([string]$Name) {
  $t = Get-NamedTask $Name
  if (-not $t) { return }
  if (Test-TaskPointsHere $t) {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false
    Write-Host "Removed stale task $Name (pointed at this copy)"
    return
  }
  $p = Get-TaskBootPath $t
  if ($p -and -not (Test-Path -LiteralPath $p)) {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false
    Write-Host "Removed orphan task $Name (missing $p)"
  }
}

function Write-PrefsEnabled {
  $prefsPath = Join-Path $LiveRoot "results\autostart_prefs.json"
  New-Item -ItemType Directory -Path (Split-Path $prefsPath) -Force | Out-Null
  $prefs = @{
    enabled = $true
    start_mt5 = $true
    start_app = $true
    start_bridge = $true
    delay_sec = $DelaySec
    port = $Port
    updated_at = (Get-Date).ToString("o")
    task_name = $TaskName
  }
  if (Test-Path $prefsPath) {
    try {
      $cur = Get-Content $prefsPath -Raw | ConvertFrom-Json
      if ($null -ne $cur.start_bridge) { $prefs.start_bridge = [bool]$cur.start_bridge }
      if ($null -ne $cur.start_mt5) { $prefs.start_mt5 = [bool]$cur.start_mt5 }
      if ($null -ne $cur.start_app) { $prefs.start_app = [bool]$cur.start_app }
    } catch {}
  }
  ($prefs | ConvertTo-Json -Depth 4) | Set-Content $prefsPath -Encoding utf8
}

function Invoke-Install {
  $existing = Get-NamedTask $TaskName
  if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  }

  $arg = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-WindowStyle", "Hidden",
    "-File", "`"$BootScript`"",
    "-DelaySec", "$DelaySec",
    "-Port", "$Port"
  ) -join " "

  # NOTE: do not name this $Action - that shadows the -Action param (ValidateSet)
  # and PowerShell then rejects MSFT_TaskExecAction as an invalid Action value.
  $taskAction = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $arg `
    -WorkingDirectory $LiveRoot

  $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
  $settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

  $principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

  Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $taskAction `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "EdgeMiner Live: start XM MT5 + Live app + bridge after Windows logon" `
    -Force | Out-Null

  if ($TaskName -ne $LegacyTaskName) {
    Remove-StaleNamedTask $LegacyTaskName
  }

  Write-PrefsEnabled
  Write-Host ("INSTALLED: {0} (AtLogOn user={1} delay={2}s port={3})" -f `
    $TaskName, $env:USERNAME, $DelaySec, $Port)
  Write-Host "Path=$BootScript"
  Write-Host "Boot script: $BootScript"
  Write-Host "Test now: powershell -ExecutionPolicy Bypass -File `"$BootScript`" -DelaySec 2"
}

switch ($Action) {
  "Status" {
    $task = Get-NamedTask $TaskName
    if ($task) {
      $info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
      $path = Get-TaskBootPath $task
      Write-Host ("INSTALLED: {0} State={1} LastResult={2} Path={3}" -f `
        $TaskName, $task.State, $(if ($info) { $info.LastTaskResult } else { "?" }), $path)
      exit 0
    }
    Write-Host "NOT_INSTALLED: $TaskName"
    exit 1
  }

  "Uninstall" {
    $task = Get-NamedTask $TaskName
    if ($task) {
      Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
      Write-Host "Removed Scheduled Task $TaskName"
    } else {
      Write-Host "Task $TaskName already absent"
    }
    if ($TaskName -ne $LegacyTaskName) {
      Remove-StaleNamedTask $LegacyTaskName
    }
    exit 0
  }

  "Install" {
    Invoke-Install
    exit 0
  }

  "Ensure" {
    $task = Get-NamedTask $TaskName
    if ($task -and (Test-TaskPointsHere $task)) {
      Write-Host ("ALREADY_OK: {0} Path={1}" -f $TaskName, $BootScript)
      Write-Host "INSTALLED: $TaskName Path=$BootScript"
      exit 0
    }
    Invoke-Install
    exit 0
  }
}
