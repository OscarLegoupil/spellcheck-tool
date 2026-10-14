@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -File "%~dp0scripts\setup-windows.ps1"
if errorlevel 1 (
  echo.
  echo Setup did not finish. Read the message above.
  echo If Windows says the script is not digitally signed, right-click the downloaded ZIP,
  echo choose Properties, select Unblock, apply, and extract it again before retrying.
  echo If your company blocks PowerShell scripts or portable programs, ask IT to allow this application.
  pause
  exit /b 1
)
echo.
echo Setup complete. Double-click Start.cmd to open Spellcheck Tool.
pause
