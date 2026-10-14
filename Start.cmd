@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.runtime\python\python.exe" (
  echo Please run Setup.cmd first.
  pause
  exit /b 1
)
"%~dp0.runtime\python\python.exe" -m spellcheck_tool serve
if errorlevel 1 pause
