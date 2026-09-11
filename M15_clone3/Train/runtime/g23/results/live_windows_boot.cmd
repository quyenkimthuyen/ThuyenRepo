@echo off
setlocal
rem Paths are relative to this file (Train\runtime\<desk>\results)
set "APP_ROOT=%~dp0..\..\.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%APP_ROOT%\scripts\live_windows_boot.ps1" -Desk g23
