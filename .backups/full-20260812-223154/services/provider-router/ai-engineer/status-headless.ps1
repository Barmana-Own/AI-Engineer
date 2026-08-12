#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$connection = Get-NetTCPConnection `
    -LocalPort 8020 `
    -State Listen `
    -ErrorAction SilentlyContinue |
    Select-Object -First 1

if (-not $connection) {
    Write-Host "Provider Hub: STOPPED" -ForegroundColor Red
    exit 1
}

Write-Host "Provider Hub: RUNNING" -ForegroundColor Green
Write-Host "PID: $($connection.OwningProcess)"
Write-Host "API: http://127.0.0.1:8020/v1"

$response = Invoke-WebRequest `
    -Method Get `
    -Uri "http://127.0.0.1:8020" `
    -UseBasicParsing `
    -TimeoutSec 10

Write-Host "HTTP status: $($response.StatusCode)"