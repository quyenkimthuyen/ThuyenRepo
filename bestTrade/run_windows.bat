@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_CMD="
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo Python was not found. Install Python 3 and make sure it is available in PATH.
    exit /b 1
)

if not exist "..\systemtrain\" (
    echo SystemTrain was not found at "%~dp0..\systemtrain".
    echo BestTrade requires the systemtrain project as a sibling directory.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
)

call ".venv\Scripts\activate.bat"
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"

echo Installing dependencies...
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo Starting BestTrade...
python -m streamlit run run_app.py --server.headless=true --browser.gatherUsageStats=false
