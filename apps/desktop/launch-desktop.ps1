#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$configuredRoot = if (-not [string]::IsNullOrWhiteSpace($env:AI_ENGINE_PROJECT_ROOT)) { $env:AI_ENGINE_PROJECT_ROOT } elseif (-not [string]::IsNullOrWhiteSpace($env:PROJECT_ROOT)) { $env:PROJECT_ROOT } else { $null }
$root = if (-not [string]::IsNullOrWhiteSpace($configuredRoot)) { (Resolve-Path -LiteralPath $configuredRoot).Path } elseif (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) { (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path } else { throw "Could not resolve the AI Engineer repository root." }
$env:AI_ENGINE_PROJECT_ROOT = $root
$appRoot = "$root\apps\desktop"

function Port-Is-Open([int]$Port) {
    return $null -ne (
        Get-NetTCPConnection `
            -LocalPort $Port `
            -State Listen `
            -ErrorAction SilentlyContinue |
        Select-Object -First 1
    )
}

function Wait-Port([int]$Port, [int]$Seconds = 60) {
    $deadline = (Get-Date).AddSeconds($Seconds)

    while ((Get-Date) -lt $deadline) {
        if (Port-Is-Open $Port) {
            return $true
        }

        Start-Sleep -Seconds 1
    }

    return $false
}

if (-not (Port-Is-Open 11434)) {
    $ollama = @(
        "$root\tools\Ollama\ollama.exe",
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    ) |
        Where-Object { Test-Path -LiteralPath $_ } |
        Select-Object -First 1

    if (-not $ollama) {
        throw "Ollama پیدا نشد."
    }

    $env:OLLAMA_MODELS = "$root\models\ollama"

    Start-Process `
        -FilePath $ollama `
        -ArgumentList "serve" `
        -WindowStyle Hidden

    if (-not (Wait-Port 11434 60)) {
        throw "Ollama اجرا نشد."
    }
}

if (-not (Port-Is-Open 8010)) {
    $serviceRoot = "$root\services\model-gateway"
    $python = "$serviceRoot\.venv\Scripts\python.exe"

    $env:BARMANA_BASE_URL = "http://127.0.0.1:11434/v1"
    $env:BARMANA_API_KEY = "ollama"
    $env:BARMANA_AUTH_MODE = "bearer"
    $env:BARMANA_MODELS_PATH = "/models"
    $env:BARMANA_CHAT_PATH = "/chat/completions"
    $env:DEFAULT_MODEL = "qwen2.5-coder:1.5b"
    $env:FALLBACK_MODELS = ""
    $env:MAX_FALLBACK_ATTEMPTS = "1"
    $env:READ_TIMEOUT_SECONDS = "300"
    $env:NO_PROXY = "localhost,127.0.0.1,::1"

    Start-Process `
        -FilePath $python `
        -ArgumentList @(
            "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1",
            "--port", "8010",
            "--workers", "1"
        ) `
        -WorkingDirectory $serviceRoot `
        -WindowStyle Hidden

    if (-not (Wait-Port 8010 60)) {
        throw "Model Gateway اجرا نشد."
    }
}

if (-not (Port-Is-Open 8011)) {
    $serviceRoot = "$root\services\local-agent"

    Start-Process `
        -FilePath "$serviceRoot\.venv\Scripts\python.exe" `
        -ArgumentList @(
            "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1",
            "--port", "8011",
            "--workers", "1"
        ) `
        -WorkingDirectory $serviceRoot `
        -WindowStyle Hidden

    if (-not (Wait-Port 8011 60)) {
        throw "Local Agent اجرا نشد."
    }
}

if (-not (Port-Is-Open 8012)) {
    $serviceRoot = "$root\services\orchestrator"

    Start-Process `
        -FilePath "$serviceRoot\.venv\Scripts\python.exe" `
        -ArgumentList @(
            "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1",
            "--port", "8012",
            "--workers", "1"
        ) `
        -WorkingDirectory $serviceRoot `
        -WindowStyle Hidden

    if (-not (Wait-Port 8012 60)) {
        throw "Orchestrator اجرا نشد."
    }
}

Set-Location $appRoot
& "$appRoot\node_modules\.bin\electron.cmd" .
