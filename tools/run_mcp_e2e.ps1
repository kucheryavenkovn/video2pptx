# tools/run_mcp_e2e.ps1
# Windows PowerShell runner for MCP E2E tests
param(
    [Parameter(Mandatory=$true)]
    [string]$Repo,
    [Parameter(Mandatory=$true)]
    [string]$Video,
    [Parameter(Mandatory=$true)]
    [string]$Subtitles,
    [string]$Workspace = "$env:TEMP\video2pptx-e2e",
    [string]$Report = "",
    [switch]$OpenReport
)

$ErrorActionPreference = "Stop"

# Resolve paths
$Repo = Resolve-Path $Repo
$Video = Resolve-Path $Video
$Subtitles = Resolve-Path $Subtitles

if (-not $Report) {
    $Report = "$Workspace\report"
}

# Activate venv if exists
$venv = "$Repo\.venv\Scripts\Activate.ps1"
if (Test-Path $venv) {
    & $venv
}

# Create workspace
New-Item -ItemType Directory -Path $Workspace -Force | Out-Null

Write-Host "=== MCP E2E Runner ===" -ForegroundColor Cyan
Write-Host "Repo: $Repo"
Write-Host "Video: $Video"
Write-Host "Subtitles: $Subtitles"
Write-Host "Workspace: $Workspace"
Write-Host "Report: $Report"
Write-Host ""

# Run the E2E runner
$runner = Join-Path $Repo "tools\mcp_e2e_runner.py"
if (Test-Path $runner) {
    python $runner `
        --repo "$Repo" `
        --video "$Video" `
        --subtitles "$Subtitles" `
        --workspace "$Workspace" `
        --report "$Report"
    $exitCode = $LASTEXITCODE
    Write-Host "Runner exit code: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Red" })
} else {
    Write-Host "Runner script not found: $runner" -ForegroundColor Yellow
    Write-Host "Running pytest E2E scenarios directly..." -ForegroundColor Yellow
    python -m pytest tests/e2e/ -v --tb=long
    $exitCode = $LASTEXITCODE
}

if ($OpenReport -and (Test-Path "$Report\summary.html")) {
    Start-Process "$Report\summary.html"
}

exit $exitCode
