#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$PythonCommand = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ServiceRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ServiceRoot

Write-Host "Model Gateway setup" -ForegroundColor Cyan
Write-Host "Directory: $ServiceRoot"

$Python = Get-Command $PythonCommand -ErrorAction SilentlyContinue
if (-not $Python) {
    throw "Python command was not found: $PythonCommand"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating local virtual environment..." -ForegroundColor Cyan
    & $Python.Source -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python virtual environment."
    }
}

$VenvPython = Join-Path $ServiceRoot ".venv\Scripts\python.exe"

Write-Host "Installing dependencies inside the project virtual environment..." -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed."
}

& $VenvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed."
}

Write-Host "Running tests..." -ForegroundColor Cyan
& $VenvPython -m pytest
if ($LASTEXITCODE -ne 0) {
    throw "Tests failed."
}

Write-Host ""
Write-Host "Setup and tests completed successfully." -ForegroundColor Green
Write-Host "No package was installed globally or with Administrator access."
