@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.runtime\python\python.exe" (
  echo Please run Setup.cmd first.
  pause
  exit /b 1
)
"%~dp0.runtime\python\python.exe" -m streamlit run src\spellcheck_tool\streamlit_app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
if errorlevel 1 pause
