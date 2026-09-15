#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8010,

    [switch]$Reload
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    chcp 65001 | Out-Null
    [Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {
}

$ServiceRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ServiceRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment not found. Run .\scripts\setup.ps1 first."
}

Set-Location $ServiceRoot

$env:BARMANA_BASE_URL = "https://api.codemain.ir/v2/api"
$env:BARMANA_AUTH_MODE = "bearer"
$env:BARMANA_MODELS_PATH = "/models"
$env:BARMANA_CHAT_PATH = "/chat/completions"
$env:DEFAULT_MODEL = "mistral-small-latest"
$env:FALLBACK_MODELS = "mistral-medium-latest,auto,codestral-latest"
$env:GATEWAY_HOST = "127.0.0.1"
$env:GATEWAY_PORT = "$Port"

$secureKey = $null
$bstr = [IntPtr]::Zero
$plainKey = $null

try {
    if ([string]::IsNullOrWhiteSpace($env:BARMANA_API_KEY)) {
        Write-Host "The API key is kept only in this process." -ForegroundColor Yellow
        $secureKey = Read-Host "Enter Barmana API key" -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
        $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)

        if ([string]::IsNullOrWhiteSpace($plainKey)) {
            throw "API key cannot be empty."
        }

        $env:BARMANA_API_KEY = $plainKey
    }

    $arguments = @(
        "-m", "uvicorn",
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", "$Port",
        "--workers", "1"
    )

    if ($Reload) {
        $arguments += "--reload"
    }

    Write-Host ""
    Write-Host "Starting Model Gateway v0.2.1" -ForegroundColor Green
    Write-Host "Local URL: http://127.0.0.1:$Port"
    Write-Host "Swagger:   http://127.0.0.1:$Port/docs"
    Write-Host "Default model: mistral-small-latest"
    Write-Host "Fallbacks: mistral-medium-latest, auto, codestral-latest"
    Write-Host "Press Ctrl+C to stop."
    Write-Host ""

    & $VenvPython @arguments
}
finally {
    $plainKey = $null
    Remove-Item Env:\BARMANA_API_KEY -ErrorAction SilentlyContinue

    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }

    if ($secureKey) {
        $secureKey.Dispose()
    }
}
