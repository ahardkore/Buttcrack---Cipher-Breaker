@echo off
rem Double-clickable wrapper around build.ps1, for when you do not want to
rem think about PowerShell execution policy.
rem
rem    build.bat              normal build
rem    build.bat -Clean       throw away dist\, build\ and the build venv first
rem
rem Output: dist\installer\buttcrack-setup-<version>.exe

setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
set EXITCODE=%ERRORLEVEL%

if %EXITCODE% NEQ 0 (
  echo.
  echo Build failed with exit code %EXITCODE%.
)
echo.
pause
exit /b %EXITCODE%
