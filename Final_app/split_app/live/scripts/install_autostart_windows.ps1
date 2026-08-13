# Install / uninstall Windows logon Scheduled Task for Live boot autostart.
#
#   .\install_autostart_windows.ps1 -Action Install
#   .\install_autostart_windows.ps1 -Action Uninstall
#   .\install_autostart_windows.ps1 -Action Status
#
[CmdletBinding()]
param(
  [ValidateSet("Install", "Uninstall", "Status")]
  [string]$Action = "Status",
  [int]$DelaySec = 45,
  [int]$Port = 8601
)

$ErrorActionPreference = "Stop"
$TaskName = "EdgeMinerLiveBoot"
$BootScript = Join-Path $PSScriptRoot "boot_autostart_windows.ps1"
$LiveRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not (Test-Path $BootScript)) {
  throw "Missing boot script: $BootScript"
}

function Get-TaskState {
  $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if (-not $task) { return $null }
  return $task
}

switch ($Action) {
  "Status" {
    $task = Get-TaskState
    if ($task) {
      $info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
      Write-Host ("INSTALLED: {0} State={1} LastResult={2}" -f `
        $TaskName, $task.State, $(if ($info) { $info.LastTaskResult } else { "?" }))
      exit 0
    }
    Write-Host "NOT_INSTALLED: $TaskName"
    exit 1
  }

  "Uninstall" {
    $task = Get-TaskState
    if ($task) {
      Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
      Write-Host "Removed Scheduled Task $TaskName"
    } else {
      Write-Host "Task $TaskName already absent"
    }
    exit 0
  }

  "Install" {
    # Remove old task then create fresh
    $existing = Get-TaskState
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

    $action = New-ScheduledTaskAction `
      -Execute "powershell.exe" `
      -Argument $arg `
      -WorkingDirectory $LiveRoot

    # At current user logon — MT5/UI need interactive session
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
      -Action $action `
      -Trigger $trigger `
      -Settings $settings `
      -Principal $principal `
      -Description "EdgeMiner Live: start XM MT5 + Live app after Windows logon" `
      -Force | Out-Null

    # Persist prefs enabled
    $prefsPath = Join-Path $LiveRoot "results\autostart_prefs.json"
    New-Item -ItemType Directory -Path (Split-Path $prefsPath) -Force | Out-Null
    $prefs = @{
      enabled = $true
      start_mt5 = $true
      start_app = $true
      start_bridge = $false
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

    Write-Host "INSTALLED: $TaskName (AtLogOn user=$env:USERNAME delay=${DelaySec}s port=$Port)"
    Write-Host "Boot script: $BootScript"
    Write-Host "Test now: powershell -ExecutionPolicy Bypass -File `"$BootScript`" -DelaySec 2"
    exit 0
  }
}
