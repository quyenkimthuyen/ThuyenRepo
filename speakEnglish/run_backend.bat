@echo off
setlocal EnableExtensions

rem PronounceLab — start backend (Windows), khong kill process cu

set "BACKEND=%~dp0backend"
set "PORT=8000"
set "HOST=127.0.0.1"

if not exist "%BACKEND%" (
  echo ERROR: Khong tim thay thu muc backend: %BACKEND%
  exit /b 1
)

cd /d "%BACKEND%"

if not exist ".venv\Scripts\python.exe" (
  echo Tao virtualenv...
  py -3 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
) else (
  call ".venv\Scripts\activate.bat"
)

echo.
echo PronounceLab backend: http://%HOST%:%PORT%
echo Health: http://%HOST%:%PORT%/api/v1/health
echo.

uvicorn main:app --host %HOST% --port %PORT% --reload
endlocal
