#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Restart
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$serviceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$serverEntry = Join-Path $serviceRoot "server\dist\index.js"
$clientDist = Join-Path $PSScriptRoot "headless-client"

function Get-RouterProcesses {
    return @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -eq "node.exe" -and
                $_.CommandLine -and
                (
                    $_.CommandLine -like "*$serviceRoot*" -or
                    $_.CommandLine -like "*server\dist\index.js*"
                )
            }
    )
}

$existing = Get-RouterProcesses

if ($existing.Count -gt 0) {
    if (-not $Restart) {
        throw "Provider Hub is already running. Use -Restart to replace the existing process."
    }

    foreach ($process in $existing) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }

    Start-Sleep -Seconds 2
}

$portOwner = Get-NetTCPConnection `
    -LocalPort 8020 `
    -State Listen `
    -ErrorAction SilentlyContinue |
    Select-Object -First 1

if ($portOwner) {
    throw "Port 8020 is already in use by PID $($portOwner.OwningProcess)."
}

if (-not (Test-Path -LiteralPath $serverEntry)) {
    throw "Production server build is missing: $serverEntry"
}

$env:NODE_ENV = "production"
$env:HOST = "127.0.0.1"
$env:PORT = "8020"
$env:CLIENT_DIST = $clientDist

Set-Location $serviceRoot

Write-Host ""
Write-Host "AI Engineer Provider Hub" -ForegroundColor Green
Write-Host "API:    http://127.0.0.1:8020/v1"
Write-Host "Status: http://127.0.0.1:8020"
Write-Host "Mode:   Headless production"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

& node $serverEntry
exit $LASTEXITCODE