#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$serviceRoot = [IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..")
)

$npm = Get-Command npm -ErrorAction SilentlyContinue |
    Select-Object -First 1

if (-not $npm) {
    throw "npm is not available in PATH."
}

if (-not (Test-Path -LiteralPath (Join-Path $serviceRoot "node_modules"))) {
    throw "node_modules is missing. Run npm install in $serviceRoot"
}

Set-Location $serviceRoot

Write-Host ""
Write-Host "Starting AI Engineer Provider Router..." -ForegroundColor Green
Write-Host "Dashboard: http://127.0.0.1:5173"
Write-Host "API:       http://127.0.0.1:8020/v1"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

& $npm.Source run dev
exit $LASTEXITCODE