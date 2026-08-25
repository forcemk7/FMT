@echo off
title FMT
cd /d "%~dp0"

set "VCVARS=%ProgramFiles(x86)%\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%VCVARS%" (
  echo Missing: %VCVARS%
  echo Install VS Build Tools 2022 with Desktop C++ / Windows SDK.
  pause
  exit /b 1
)

call "%VCVARS%"
if errorlevel 1 (
  echo vcvars64 failed.
  pause
  exit /b 1
)

where cargo >nul 2>&1
if errorlevel 1 set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
where cargo >nul 2>&1
if errorlevel 1 (
  echo cargo not found. Install Rust from https://rustup.rs
  pause
  exit /b 1
)

echo.
echo Starting FMT (stable) from: %CD%
echo Use the desktop window (not the browser tab).
echo This launch uses --no-watch so Cursor/file saves do not kill the window.
echo Closing the FMT window exits normally. Ctrl+C in this console also quits.
echo.
call npm run desktop:stable
echo.
pause
