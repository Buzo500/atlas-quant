@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Atlas.ps1" -OpenBrowser
if errorlevel 1 pause
