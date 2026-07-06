param(
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "Starting SystemTrain Streamlit app on port $Port..."

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $listeners) {
    $processId = $listener.OwningProcess
    if ($processId) {
        Write-Host "Stopping existing process $processId on port $Port..."
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Ensuring Python dependencies are installed..."
python -m pip install -r requirements.txt

Write-Host "Launching Streamlit..."
python -m streamlit run run_app.py --server.port $Port --server.headless true
