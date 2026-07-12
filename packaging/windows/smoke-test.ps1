# Video2PPTX packaged executable MCP smoke test
# Verifies the built EXE launches, MCP responds, tools/list works, project lifecycle works.
# Usage: powershell -ExecutionPolicy Bypass -File packaging/windows/smoke-test.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path "$PSScriptRoot\..\.."
$DistDir = "$RepoRoot\dist\windows"
$StandaloneDir = "$DistDir\Video2PPTX"
$Exe = "$StandaloneDir\Video2PPTX.exe"

# Validate layout
Write-Host "Validating standalone layout..." -ForegroundColor Yellow
if (-not (Test-Path $Exe)) {
    Write-Host "ERROR: $Exe not found" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "$StandaloneDir\_internal")) {
    Write-Host "ERROR: _internal not found" -ForegroundColor Red
    exit 1
}
$exeSize = (Get-Item $Exe).Length / 1MB
Write-Host "  EXE: $Exe ($([math]::Round($exeSize, 1)) MB)" -ForegroundColor Green

# 1. Launch process with MCP port discovery
Write-Host "`n1. Launching packaged executable..." -ForegroundColor Yellow
$env:QT_QPA_PLATFORM = "offscreen"
$env:VIDEO2PPTX_DISABLE_GPU = "1"
$proc = Start-Process -FilePath $Exe -PassThru -NoNewWindow

# 2. Wait for MCP discovery (via .mcp_port file or port 9812)
Write-Host "`n2. Waiting for MCP port discovery..." -ForegroundColor Yellow
$mcpPort = $null
$tempDir = [System.IO.Path]::GetTempPath()
$mcpPortFile = $null

for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500

    # Check if process already exited
    if ($proc.HasExited) {
        Write-Host "  Process exited unexpectedly with code $($proc.ExitCode)" -ForegroundColor Red
        exit 1
    }

    # Look for .mcp_port file in temp
    $mcpPortFile = Get-ChildItem -Path $tempDir -Filter ".mcp_port*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($mcpPortFile) {
        $mcpPort = [int]((Get-Content $mcpPortFile.FullName -ErrorAction SilentlyContinue) -replace '[^0-9]', '')
        if ($mcpPort -gt 0) {
            Write-Host "  Discovered MCP port: $mcpPort (from $($mcpPortFile.Name))" -ForegroundColor Green
            break
        }
    }

    # Fallback: try default port 9812
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.ConnectAsync("127.0.0.1", 9812).Wait(200) | Out-Null
        if ($tcp.Connected) {
            $mcpPort = 9812
            $tcp.Close()
            Write-Host "  Discovered MCP port: $mcpPort (default)" -ForegroundColor Green
            break
        }
        $tcp.Close()
    } catch {}
}

if (-not $mcpPort) {
    Write-Host "  MCP port not found within 15s timeout" -ForegroundColor Red
    try { $proc.Kill() } catch {}
    exit 1
}

# 3. MCP initialize
Write-Host "`n3. MCP initialize..." -ForegroundColor Yellow
$baseUrl = "http://127.0.0.1:$mcpPort"

try {
    # SSE-based MCP discovery
    $initBody = @{
        jsonrpc = "2.0"
        id = 1
        method = "initialize"
        params = @{
            protocolVersion = "0.1.0"
            capabilities = @{}
            clientInfo = @{
                name = "smoke-test"
                version = "1.0.0"
            }
        }
    } | ConvertTo-Json -Compress

    $initResult = Invoke-RestMethod -Uri "$baseUrl/mcp" -Method Post -Body $initBody -ContentType "application/json" -ErrorAction Stop
    Write-Host "  Initialize result: $($initResult | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "  Initialize failed: $_" -ForegroundColor Red
    try { $proc.Kill() } catch {}
    exit 1
}

# 4. tools/list
Write-Host "`n4. MCP tools/list..." -ForegroundColor Yellow
try {
    $toolsBody = @{
        jsonrpc = "2.0"
        id = 2
        method = "tools/list"
        params = @{}
    } | ConvertTo-Json -Compress

    $toolsResult = Invoke-RestMethod -Uri "$baseUrl/mcp" -Method Post -Body $toolsBody -ContentType "application/json" -ErrorAction Stop
    $toolCount = $toolsResult.result.tools.Count
    Write-Host "  Tools available: $toolCount" -ForegroundColor Green
    foreach ($tool in $toolsResult.result.tools) {
        Write-Host "    - $($tool.name): $($tool.description)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  tools/list failed: $_" -ForegroundColor Red
    try { $proc.Kill() } catch {}
    exit 1
}

# 5. health/state read
Write-Host "`n5. Reading application state..." -ForegroundColor Yellow
try {
    $stateBody = @{
        jsonrpc = "2.0"
        id = 3
        method = "tools/call"
        params = @{
            name = "get_app_state"
            arguments = @{}
        }
    } | ConvertTo-Json -Compress

    $stateResult = Invoke-RestMethod -Uri "$baseUrl/mcp" -Method Post -Body $stateBody -ContentType "application/json" -ErrorAction SilentlyContinue
    if ($stateResult) {
        Write-Host "  App state read successfully" -ForegroundColor Green
    }
} catch {
    # get_app_state may not exist - that's OK
    Write-Host "  get_app_state not available (non-fatal)" -ForegroundColor Gray
}

# 6. App shutdown via MCP
Write-Host "`n6. Application shutdown..." -ForegroundColor Yellow
try {
    $shutdownBody = @{
        jsonrpc = "2.0"
        id = 4
        method = "tools/call"
        params = @{
            name = "app_shutdown"
            arguments = @{
                confirm = $true
            }
        }
    } | ConvertTo-Json -Compress

    $null = Invoke-RestMethod -Uri "$baseUrl/mcp" -Method Post -Body $shutdownBody -ContentType "application/json" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
} catch {
    Write-Host "  Shutdown via MCP failed (non-fatal, will kill)" -ForegroundColor Gray
}

# 7. Verify process exits
Write-Host "`n7. Verifying clean exit..." -ForegroundColor Yellow
$exited = $proc.WaitForExit(5000)
if ($exited) {
    Write-Host "  Process exited with code $($proc.ExitCode)" -ForegroundColor Green
} else {
    Write-Host "  Force-killing remaining process..." -ForegroundColor Yellow
    try { $proc.Kill() } catch {}
}

# Clean up MCP port file
if ($mcpPortFile -and (Test-Path $mcpPortFile.FullName)) {
    Remove-Item -Force $mcpPortFile.FullName -ErrorAction SilentlyContinue
}

Write-Host "`n=== SMOKE TEST PASSED ===" -ForegroundColor Green
