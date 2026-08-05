@echo off
setlocal EnableExtensions
REM manage_clones.cmd Start|Stop|Restart|Status|DeployEA [A6 A7 A8|All]
REM Examples:
REM   manage_clones.cmd Status
REM   manage_clones.cmd Start
REM   manage_clones.cmd Restart A6 A8
REM   manage_clones.cmd Stop All
REM   manage_clones.cmd DeployEA
REM Note: DeployEA flags (-Attach, -EnableTrading, -Mode, ...) need manage_clones.ps1.
set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%manage_clones.ps1"
set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=Status"
if not "%~1"=="" shift /1

set "APPS="
:collect
if "%~1"=="" goto run
if defined APPS (
  set "APPS=%APPS%,%~1"
) else (
  set "APPS=%~1"
)
shift /1
goto collect

:run
pushd "%SCRIPT_DIR%" >nul
if not defined APPS (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Action "%ACTION%"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Action "%ACTION%" -Apps "%APPS%"
)
set "ERR=%ERRORLEVEL%"
popd >nul
exit /b %ERR%
