# PyInstaller build script for Video2PPTX
# Requires: pip install pyinstaller
# Build: powershell -ExecutionPolicy Bypass -File packaging/windows/pyinstaller/build.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path "$PSScriptRoot\..\..\.."
$DistDir = "$RepoRoot\dist\windows"
$Version = & python -c "import sys; sys.path.insert(0,'src'); from video2pptx import __version__; print(__version__)"

Write-Host "Building Video2PPTX $Version with PyInstaller..." -ForegroundColor Green

# Clean
if (Test-Path "$DistDir\Video2PPTX") { Remove-Item -Recurse -Force "$DistDir\Video2PPTX" }

# Build
pyinstaller --clean --noconfirm "$PSScriptRoot\video2pptx.spec"

if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

Write-Host "PyInstaller build complete." -ForegroundColor Green
