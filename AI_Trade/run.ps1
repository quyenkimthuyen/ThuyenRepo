[CmdletBinding()]
param(
    [ValidateSet("start", "restart", "stop")]
    [string]$Action = "restart",

    [string]$HostAddress = "127.0.0.1",

    [int]$Port = 8766
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Get-ListeningProcessIds {
    param([int]$TargetPort)

    $connections = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        return @()
    }

    return @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Stop-AppOnPort {
    param([int]$TargetPort)

    $processIds = Get-ListeningProcessIds -TargetPort $TargetPort
    if ($processIds.Count -eq 0) {
        Write-Host "No running app found on port $TargetPort."
        return
    }

    foreach ($processId in $processIds) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($null -eq $process) {
            continue
        }

        Write-Host "Stopping $($process.ProcessName) process $processId on port $TargetPort..."
        Stop-Process -Id $processId -Force
    }

    Start-Sleep -Seconds 1
}

function Ensure-MarketData {
    if (Test-Path "data/eurusd_h1.csv") {
        return
    }

    Write-Host "Fetching EURUSD H1 data..."
    python scripts/fetch_data.py
}

if ($Action -in @("restart", "stop")) {
    Stop-AppOnPort -TargetPort $Port
}

if ($Action -eq "stop") {
    exit 0
}

if ($Action -eq "start" -and (Get-ListeningProcessIds -TargetPort $Port).Count -gt 0) {
    Write-Error "Port $Port is already in use. Run '.\run.ps1 restart' to restart the app."
}

Ensure-MarketData

Write-Host "Starting AI Trade Lab at http://${HostAddress}:$Port"
python -m uvicorn backend.main:app --host $HostAddress --port $Port --reload
