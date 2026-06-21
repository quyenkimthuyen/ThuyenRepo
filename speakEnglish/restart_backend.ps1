# PronounceLab — restart FastAPI backend (Windows PowerShell)
# Usage:
#   .\restart_backend.ps1
#   .\restart_backend.ps1 -NewWindow
#   .\restart_backend.ps1 -Port 8000

param(
    [int]$Port = 8000,
    [string]$BindHost = "127.0.0.1",
    [switch]$NewWindow
)

$ErrorActionPreference = "Stop"
$BackendDir = Join-Path $PSScriptRoot "backend"

function Stop-BackendOnPort {
    param([int]$ListenPort)

    $killed = @()
    $pattern = ":$ListenPort\s+.*LISTENING"

    netstat -ano | Select-String $pattern | ForEach-Object {
        $parts = ($_.Line -split '\s+') | Where-Object { $_ -ne '' }
        $pid = [int]$parts[-1]
        if ($pid -gt 0 -and $killed -notcontains $pid) {
            Write-Host "      Kill PID $pid"
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            $killed += $pid
        }
    }

    if ($killed.Count -eq 0) {
        Write-Host "      Khong co process nao tren port $ListenPort"
    }

    Start-Sleep -Seconds 1
}

function Ensure-Venv {
    param([string]$Dir)

    $python = Join-Path $Dir ".venv\Scripts\python.exe"
    if (Test-Path $python) {
        return $python
    }

    Write-Host "      Tao .venv moi..."
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & py -3 -m venv (Join-Path $Dir ".venv")
    } else {
        & python -m venv (Join-Path $Dir ".venv")
    }

    if (-not (Test-Path $python)) {
        throw "Khong tao duoc venv. Cai Python 3.10+ va them vao PATH."
    }

    & $python -m pip install --upgrade pip
    & $python -m pip install -r (Join-Path $Dir "requirements.txt")
    return $python
}

Write-Host ""
Write-Host "=== PronounceLab: restart backend ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $BackendDir)) {
    throw "Khong tim thay thu muc backend: $BackendDir"
}

Write-Host "[1/3] Dung process dang lang nghe port $Port..."
Stop-BackendOnPort -ListenPort $Port

Write-Host "[2/3] Kiem tra virtualenv..."
$venvPython = Ensure-Venv -Dir $BackendDir

$uvicornArgs = @(
    "-m", "uvicorn",
    "main:app",
    "--host", $BindHost,
    "--port", "$Port",
    "--reload"
)

Write-Host "[3/3] Khoi dong uvicorn http://${BindHost}:$Port ..."
Write-Host "      Health: http://${BindHost}:$Port/api/v1/health"
Write-Host ""

if ($NewWindow) {
    $cmd = "cd /d `"$BackendDir`" && `"$venvPython`" -m uvicorn main:app --host $BindHost --port $Port --reload"
    Start-Process cmd.exe -ArgumentList "/k", $cmd -WindowStyle Normal
    Write-Host "Backend chay trong cua so moi. Dong cua so do de tat server."
} else {
    Push-Location $BackendDir
    try {
        & $venvPython @uvicornArgs
    } finally {
        Pop-Location
    }
}
