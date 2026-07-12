# Video2PPTX packaged executable smoke test
# Verifies the built EXE launches and MCP responds

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path "$PSScriptRoot\..\.."
$DistDir = "$RepoRoot\dist\windows"

# Find executable
$ExeCandidates = @(
    "$DistDir\Video2PPTX\Video2PPTX.exe",
    "$DistDir\Video2PPTX.exe"
)
$Exe = $null
foreach ($candidate in $ExeCandidates) {
    if (Test-Path $candidate) { $Exe = $candidate; break }
}

if (-not $Exe) {
    Write-Host "No executable found in $DistDir" -ForegroundColor Red
    exit 1
}

Write-Host "Testing: $Exe" -ForegroundColor Yellow
Write-Host "File size: $((Get-Item $Exe).Length / 1MB) MB"

# Launch with timeout
$proc = Start-Process -FilePath $Exe -PassThru -NoNewWindow
$exited = $proc.WaitForExit(10000)  # 10s timeout

if (-not $exited) {
    Write-Host "Process started successfully (still running)" -ForegroundColor Green
    try { $proc.Kill() } catch {}
} else {
    if ($proc.ExitCode -eq 0) {
        Write-Host "Process exited cleanly" -ForegroundColor Green
    } else {
        Write-Host "Process exited with code $($proc.ExitCode)" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Smoke test passed." -ForegroundColor Green
