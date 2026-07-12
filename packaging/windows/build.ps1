# Video2PPTX Windows build script
# Usage: powershell -ExecutionPolicy Bypass -File packaging/windows/build.ps1
# Options:
#   -Tool pyinstaller|nuitka  (default: pyinstaller)
#   -Clean                    (remove previous build)

param(
    [ValidateSet("pyinstaller", "nuitka")]
    [string]$Tool = "pyinstaller",
    [switch]$Clean = $false
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path "$PSScriptRoot\..\.."
$DistDir = "$RepoRoot\dist\windows"
$Version = & python -c "import sys; sys.path.insert(0,'src'); from video2pptx import __version__; print(__version__)"

Write-Host "=== Video2PPTX Windows Build ===" -ForegroundColor Cyan
Write-Host "Version: $Version"
Write-Host "Tool: $Tool"
Write-Host ""

if ($Clean -and (Test-Path $DistDir)) {
    Write-Host "Cleaning dist..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $DistDir
}

switch ($Tool) {
    "pyinstaller" {
        & "$PSScriptRoot\pyinstaller\build.ps1"
    }
    "nuitka" {
        & "$PSScriptRoot\nuitka\build.ps1"
    }
}

# Smoke test
& "$PSScriptRoot\smoke-test.ps1"

Write-Host "=== Build complete ===" -ForegroundColor Cyan
