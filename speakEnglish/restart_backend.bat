@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem PronounceLab — restart FastAPI backend (Windows)
rem Double-click hoac: restart_backend.bat [--new-window]

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "PORT=8000"
set "HOST=127.0.0.1"
set "NEW_WINDOW=0"
if /I "%~1"=="--new-window" set "NEW_WINDOW=1"

echo.
echo === PronounceLab: restart backend ===
echo.

echo [1/3] Dung process dang lang nghe port %PORT%...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PORT% " ^| findstr LISTENING') do (
  echo       Kill PID %%P
  taskkill /F /PID %%P >nul 2>&1
)
timeout /t 1 /nobreak >nul

if not exist "%BACKEND%" (
  echo ERROR: Khong tim thay thu muc backend: %BACKEND%
  exit /b 1
)

cd /d "%BACKEND%"

echo [2/3] Kiem tra virtualenv...
if not exist ".venv\Scripts\python.exe" (
  echo       Tao .venv moi...
  py -3 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
  if errorlevel 1 (
    echo ERROR: Khong tao duoc venv. Cai Python 3.10+ va them vao PATH.
    exit /b 1
  )
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
) else (
  call ".venv\Scripts\activate.bat"
)

echo [3/3] Khoi dong uvicorn http://%HOST%:%PORT% ...
echo       Health: http://%HOST%:%PORT%/api/v1/health
echo.

if "%NEW_WINDOW%"=="1" (
  start "PronounceLab Backend" cmd /k "cd /d \"%BACKEND%\" && call .venv\Scripts\activate.bat && uvicorn main:app --host %HOST% --port %PORT% --reload"
  echo Backend chay trong cua so moi. Dong cua so do de tat server.
) else (
  uvicorn main:app --host %HOST% --port %PORT% --reload
)

endlocal
