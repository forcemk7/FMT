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
echo Wait for the FMT desktop window — ignore any browser
echo.
call npm run desktop:stable
echo.
pause
