# Run FMT desktop from this folder. Double-click `Start FMT.cmd` instead if you prefer.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$vcvars = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $vcvars)) { throw "Missing $vcvars" }
cmd /c "`"$vcvars`" && set PATH=%USERPROFILE%\.cargo\bin;%PATH% && npm run desktop:dev"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
