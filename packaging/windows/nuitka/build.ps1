# Nuitka/PySide6-Deploy build script for Video2PPTX
# Requires: pip install nuitka pyside6-deploy
# Build: powershell -ExecutionPolicy Bypass -File packaging/windows/nuitka/build.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path "$PSScriptRoot\..\..\.."
$DistDir = "$RepoRoot\dist\windows"
$Version = & python -c "import sys; sys.path.insert(0,'src'); from video2pptx import __version__; print(__version__)"

Write-Host "Building Video2PPTX $Version with Nuitka..." -ForegroundColor Green

# Clean
if (Test-Path "$DistDir\Video2PPTX") { Remove-Item -Recurse -Force "$DistDir\Video2PPTX" }

# Build command
python -m nuitka `
    --standalone `
    --onefile `
    --output-dir="$DistDir" `
    --enable-plugin=pyside6 `
    --include-package=video2pptx `
    --include-package-data=video2pptx `
    --include-qt-plugins=sensible `
    --windows-console-mode=disable `
    --windows-icon-from-ico="" `
    --company-name="kucheryavenkovn" `
    --product-name="Video2PPTX" `
    --file-description="Video to Presentation" `
    --product-version="$Version" `
    --file-version="$Version" `
    "$RepoRoot\src\video2pptx\desktop.py"

if ($LASTEXITCODE -ne 0) { throw "Nuitka build failed" }

Write-Host "Nuitka build complete." -ForegroundColor Green
