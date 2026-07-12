[CmdletBinding()]
param(
    [ValidateSet("start", "restart", "stop")]
    [string]$Action = "start",

    [string]$HostAddress = "127.0.0.1",

    [int]$Port = 8777
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    throw "Python 3 was not found. Install Python 3 and add it to PATH."
}

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

function Test-JsonFile {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return $false
    }

    try {
        Get-Content -Path $Path -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Ensure-DataFile {
    $dataFile = Join-Path $PSScriptRoot "data\EURUSD_H1.json"
    $forexData = Join-Path $PSScriptRoot "..\Forex\data\defaults\EURUSD_H1.json"

    if (Test-JsonFile -Path $dataFile) {
        return
    }

    if (-not (Test-Path $forexData)) {
        throw "Missing EURUSD H1 data. Expected '$dataFile' or '$forexData'."
    }

    $dataDir = Split-Path $dataFile -Parent
    if (-not (Test-Path $dataDir)) {
        New-Item -ItemType Directory -Path $dataDir | Out-Null
    }

    if (Test-Path $dataFile) {
        Write-Host "Restoring invalid EURUSD H1 data from Forex..."
    }
    else {
        Write-Host "Copying EURUSD H1 data from Forex..."
    }
    Copy-Item -Path $forexData -Destination $dataFile -Force
}

function Ensure-Venv {
    $venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    Write-Host "Creating virtual environment..."
    $py = Get-PythonCommand
    & $py[0] @($py[1..($py.Length - 1)]) -m venv .venv
    return $venvPython
}

if ($Action -in @("restart", "stop")) {
    Stop-AppOnPort -TargetPort $Port
}

if ($Action -eq "stop") {
    exit 0
}

if ($Action -eq "start" -and (Get-ListeningProcessIds -TargetPort $Port).Count -gt 0) {
    throw "Port $Port is already in use. Run '.\run.ps1 restart' to restart the app."
}

Ensure-DataFile
$python = Ensure-Venv

Write-Host "Installing dependencies..."
& $python -m pip install --upgrade pip -q
& $python -m pip install -r requirements.txt -q

Write-Host "RSI Zone Analyzer -> http://${HostAddress}:$Port"
& $python -m uvicorn backend.main:app --host $HostAddress --port $Port --reload
