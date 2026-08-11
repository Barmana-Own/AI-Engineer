#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$serviceRoot = "F:\AI-Engineer\services\orchestrator"
$python = Join-Path $serviceRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Orchestrator virtual environment is missing."
}

Set-Location $serviceRoot

& $python `
    -m uvicorn `
    app.main:app `
    --host 127.0.0.1 `
    --port 8012 `
    --workers 1