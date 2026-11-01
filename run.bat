@echo off
cd /d "%~dp0"
if not exist ".venv-standard\Scripts\pythonw.exe" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
  if errorlevel 1 (pause & exit /b 1)
)
start "Pawzura" ".venv-standard\Scripts\pythonw.exe" "%~dp0run.py" --settings
