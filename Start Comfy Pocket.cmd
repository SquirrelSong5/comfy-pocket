@echo off
cd /d "%~dp0"
if exist config.json (
  powershell.exe -NoProfile -File "%~dp0start.ps1" -Open
) else (
  node cli/index.mjs
)
if errorlevel 1 pause
