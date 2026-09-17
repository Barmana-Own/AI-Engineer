#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = if (-not [string]::IsNullOrWhiteSpace($env:AI_ENGINE_PROJECT_ROOT)) { (Resolve-Path -LiteralPath $env:AI_ENGINE_PROJECT_ROOT).Path } elseif (-not [string]::IsNullOrWhiteSpace($env:PROJECT_ROOT)) { (Resolve-Path -LiteralPath $env:PROJECT_ROOT).Path } elseif (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) { (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path } else { throw "Could not resolve the AI Engineer repository root." }
$env:AI_ENGINE_PROJECT_ROOT = $repoRoot
$serviceRoot = Join-Path $repoRoot "services\orchestrator"
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