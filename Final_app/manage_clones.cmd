@echo off
setlocal EnableExtensions
REM manage_clones.cmd Start|Stop|Restart|Status|DeployEA [F1 F2 F3 F4|M15 M5|EUR GBP|All]
REM Examples:
REM   manage_clones.cmd Status
REM   manage_clones.cmd Start
REM   manage_clones.cmd Restart F3
REM   manage_clones.cmd Stop M15
REM   manage_clones.cmd DeployEA
REM   manage_clones.cmd DeployEA F1 F3
REM Note: DeployEA flags (-Attach, -Mode Both, -NoEnableTrading, ...) need manage_clones.ps1.
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
