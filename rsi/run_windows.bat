@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "PORT=8777"
if not "%RSI_PORT%"=="" set "PORT=%RSI_PORT%"

set "PYTHON_CMD="
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo Python 3 was not found. Install Python 3 and add it to PATH.
    pause
    exit /b 1
)

set "DATA_FILE=data\EURUSD_H1.json"
set "FOREX_DATA=..\Forex\data\defaults\EURUSD_H1.json"

if not exist "%DATA_FILE%" (
    if exist "%FOREX_DATA%" (
        echo Copying EURUSD H1 data from Forex...
        if not exist "data" mkdir "data"
        copy /Y "%FOREX_DATA%" "%DATA_FILE%" >nul
    ) else (
        echo Missing EURUSD H1 data.
        echo Expected: %DATA_FILE%
        echo Or run: cd ..\Forex ^&^& python scripts\fetch-default-data.py
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        pause
        exit /b %ERRORLEVEL%
    )
)

call ".venv\Scripts\activate.bat"
if %ERRORLEVEL% NEQ 0 (
    pause
    exit /b %ERRORLEVEL%
)

echo Installing dependencies...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if %ERRORLEVEL% NEQ 0 (
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo RSI Zone Analyzer -^> http://127.0.0.1:%PORT%
echo Press Ctrl+C to stop.
echo.

python -m uvicorn backend.main:app --host 127.0.0.1 --port %PORT% --reload
if %ERRORLEVEL% NEQ 0 pause
exit /b %ERRORLEVEL%
