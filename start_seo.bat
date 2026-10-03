@echo off
set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_EXE%" set "PS_EXE=powershell.exe"
"%PS_EXE%" -ExecutionPolicy Bypass -NoProfile -File "%~dp0start_seo.ps1"
if errorlevel 1 pause
