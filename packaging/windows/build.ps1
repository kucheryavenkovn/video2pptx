# Video2PPTX Windows Release Build
# Usage: powershell -ExecutionPolicy Bypass -File packaging/windows/build.ps1
# Options:
#   -Clean                    (remove previous build artifacts)
#   -SkipSmokeTest            (skip verification after build)

param(
    [switch]$Clean = $false,
    [switch]$SkipSmokeTest = $false
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path "$PSScriptRoot\..\.."
$DistDir = "$RepoRoot\dist\windows"
$StandaloneDir = "$DistDir\Video2PPTX"

Write-Host "=== VIDEO2PPTX WINDOWS BUILD ===" -ForegroundColor Cyan

# 1. Validate Windows build environment
Write-Host "`n[1/9] Validating build environment..." -ForegroundColor Yellow
if ($env:OS -notlike "*Windows*") {
    throw "Build requires Windows"
}
$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "  Python: $pythonVersion"

# 2. Resolve canonical package version
Write-Host "`n[2/9] Resolving package version..." -ForegroundColor Yellow
$Version = & python -c "import sys; sys.path.insert(0,'src'); from video2pptx import __version__; print(__version__)"
if (-not $Version) { throw "Cannot resolve package version" }
Write-Host "  Version: $Version"

# 3. Validate release dependencies
Write-Host "`n[3/9] Validating release dependencies..." -ForegroundColor Yellow
$imports = @(
    "PySide6", "PySide6.QtWidgets", "cv2", "PIL", "numpy",
    "av", "pptx", "httpx", "pysubs2", "yaml", "imagehash",
    "skimage", "packaging.version"
)
foreach ($mod in $imports) {
    $result = & python -c "import $mod; print('ok')" 2>$null
    if ($result -ne "ok") { throw "Required dependency not importable: $mod" }
}
Write-Host "  All dependencies OK"

# Check Inno Setup availability
$ISCC = & {
    $paths = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "$env:ISCC_PATH"
    )
    foreach ($p in $paths) { if ($p -and (Test-Path $p)) { return $p } }
    return $null
}
if (-not $ISCC) {
    throw "Inno Setup 6 was not found. Install Inno Setup or specify ISCC_PATH."
}
Write-Host "  Inno Setup: $ISCC"

# 4. Clean staging
Write-Host "`n[4/9] Cleaning staging..." -ForegroundColor Yellow
if ($Clean -and (Test-Path $DistDir)) {
    Remove-Item -Recurse -Force $DistDir
    Write-Host "  Cleaned $DistDir"
}
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

# 5. Inject build metadata
Write-Host "`n[5/9] Injecting build metadata..." -ForegroundColor Yellow
$Sha = & git rev-parse HEAD 2>$null
if (-not $Sha) { $Sha = "unknown" }
$BuildTime = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
@"
BUILD_META = {
    "commit_sha": "$Sha",
    "build_type": "standalone",
    "packaging_tool": "pyinstaller",
    "build_time": "$BuildTime",
}
"@ | Out-File -FilePath "$RepoRoot\src\video2pptx\build_meta.py" -Encoding utf8
Write-Host "  commit_sha=$Sha  build_type=standalone"

# 6. PyInstaller onedir
Write-Host "`n[6/9] Running PyInstaller..." -ForegroundColor Yellow
$env:REPO_ROOT = $RepoRoot
pyinstaller --clean --noconfirm "$PSScriptRoot\pyinstaller\video2pptx.spec" --distpath "$DistDir"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

# 7. Validate standalone layout
Write-Host "`n[7/9] Validating standalone layout..." -ForegroundColor Yellow
$expectedPaths = @(
    "$StandaloneDir",
    "$StandaloneDir\Video2PPTX.exe",
    "$StandaloneDir\_internal"
)
foreach ($p in $expectedPaths) {
    if (-not (Test-Path $p)) { throw "Missing expected path: $p" }
}
$exeSize = (Get-Item "$StandaloneDir\Video2PPTX.exe").Length / 1MB
Write-Host "  Layout OK - EXE size: $([math]::Round($exeSize, 1)) MB"

# 8. Smoke test
if (-not $SkipSmokeTest) {
    Write-Host "`n[8/9] Running packaged smoke tests..." -ForegroundColor Yellow
    & "$PSScriptRoot\smoke-test.ps1"
    if ($LASTEXITCODE -ne 0) { throw "Smoke test failed" }
} else {
    Write-Host "`n[8/9] Skipping smoke tests" -ForegroundColor Yellow
}

# 9. Build portable ZIP
Write-Host "`n[9/9] Building release artifacts..." -ForegroundColor Yellow
$zipPath = "$DistDir\Video2PPTX-$Version-portable-x64.zip"
Compress-Archive -Path "$StandaloneDir\*" -DestinationPath $zipPath -Force
Write-Host "  Portable ZIP: $zipPath"

# 10. Build installer
$issPath = "$PSScriptRoot\installer\video2pptx.iss"
$env:VERSION = $Version
& $ISCC $issPath
if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed" }
Write-Host "  Installer: $DistDir\Video2PPTX-$Version-Setup-x64.exe"

# 11. SHA256
Write-Host "  Generating SHA256SUMS.txt..." -ForegroundColor Yellow
if (Test-Path "$DistDir\SHA256SUMS.txt") { Remove-Item -Force "$DistDir\SHA256SUMS.txt" }
Get-ChildItem "$DistDir\*.exe", "$DistDir\*.zip" | ForEach-Object {
    $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
    "$hash  $($_.Name)" | Out-File -FilePath "$DistDir\SHA256SUMS.txt" -Encoding ascii -Append
}
Get-Content "$DistDir\SHA256SUMS.txt"

Write-Host "`n=== VIDEO2PPTX WINDOWS BUILD COMPLETE ===" -ForegroundColor Green
Write-Host "Version: $Version" -ForegroundColor Cyan
Write-Host "Build SHA: $Sha" -ForegroundColor Cyan
Write-Host "Packaging: PyInstaller onedir" -ForegroundColor Cyan
Write-Host "Standalone: $((Resolve-Path $StandaloneDir).Path)" -ForegroundColor Cyan
Write-Host "Portable ZIP: $((Resolve-Path $zipPath).Path)" -ForegroundColor Cyan
$setupExe = Get-ChildItem "$DistDir\*Setup-x64.exe" | Select-Object -First 1
if ($setupExe) {
    Write-Host "Installer: $($setupExe.FullName)" -ForegroundColor Cyan
}
Write-Host "SHA256: $DistDir\SHA256SUMS.txt" -ForegroundColor Cyan
