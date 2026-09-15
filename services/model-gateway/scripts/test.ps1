#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ServiceRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ServiceRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment not found. Run .\scripts\setup.ps1 first."
}

Set-Location $ServiceRoot
& $VenvPython -m pytest
exit $LASTEXITCODE
