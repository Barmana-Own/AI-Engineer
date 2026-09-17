#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$configuredRoot = if (-not [string]::IsNullOrWhiteSpace($env:AI_ENGINE_PROJECT_ROOT)) { $env:AI_ENGINE_PROJECT_ROOT } elseif (-not [string]::IsNullOrWhiteSpace($env:PROJECT_ROOT)) { $env:PROJECT_ROOT } else { $null }
$root = if (-not [string]::IsNullOrWhiteSpace($configuredRoot)) {
    (Resolve-Path -LiteralPath $configuredRoot).Path
} elseif (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    (Resolve-Path -LiteralPath $PSScriptRoot).Path
} else {
    throw "Could not resolve the AI Engineer repository root. Set AI_ENGINE_PROJECT_ROOT or run this script from the repository root."
}
$env:AI_ENGINE_PROJECT_ROOT = $root

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
        if (Port-Is-Open $Port) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Get-ProviderHubKey {
    $python = Get-Command python -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $python) { return $null }

    $dbPath = "$root\data\provider-router\freellmapi.db"
    if (-not (Test-Path -LiteralPath $dbPath)) { return $null }

    $query = @'
import sqlite3
import sys

try:
    connection = sqlite3.connect(sys.argv[1])
    row = connection.execute(
        "SELECT value FROM settings WHERE key='unified_api_key'"
    ).fetchone()
    if row and isinstance(row[0], str):
        print(row[0])
finally:
    try:
        connection.close()
    except Exception:
        pass
'@

    try {
        $key = ($query | & $python.Source - $dbPath 2>$null).Trim()
        if ($key -match '^freellmapi-[A-Za-z0-9_-]+$') { return $key }
    }
    catch {
    }
    return $null
}

function Provider-Hub-Ready {
    if (-not (Port-Is-Open 8020)) { return $false }
    $key = Get-ProviderHubKey
    if ([string]::IsNullOrWhiteSpace($key)) { return $false }
    try {
        # A model catalogue alone is not enough: the embedded proxy can still
        # be rate-limited or have no usable upstream.  Keep Ollama as the
        # deterministic local fallback until the proxy reports a healthy pool.
        $providerRaw = & curl.exe -fsS `
            -H "Authorization: Bearer $key" `
            "http://127.0.0.1:8020/v1/providers" 2>$null
        $providerPayload = ($providerRaw -join "`n") | ConvertFrom-Json
        $providers = @($providerPayload.providers)
        if ($providers.Count -eq 0) { return $false }
        $unusable = @("rate_limited", "unavailable", "error", "disabled")
        if ($providers | Where-Object { $unusable -contains ([string]$_.status).ToLowerInvariant() }) {
            return $false
        }
        $raw = & curl.exe -fsS `
            -H "Authorization: Bearer $key" `
            "http://127.0.0.1:8020/v1/models" 2>$null
        $payload = ($raw -join "`n") | ConvertFrom-Json
        return @($payload.data).Count -gt 0
    }
    catch {
        return $false
    }
}

function Ensure-Provider-Hub {
    $routerRoot = "$root\services\provider-router"
    $serverEntry = "$routerRoot\server\dist\index.js"
    if (-not (Test-Path -LiteralPath $serverEntry)) { return $false }

    if (-not (Port-Is-Open 8020)) {
        Start-Process `
            -FilePath "node.exe" `
            -ArgumentList "dist/index.js" `
            -WorkingDirectory "$routerRoot\server" `
            -WindowStyle Hidden

        if (-not (Wait-Port 8020 45)) { return $false }
    }

    return (Provider-Hub-Ready)
}

$providerHubReady = Ensure-Provider-Hub

if (-not $providerHubReady -and -not (Port-Is-Open 11434)) {
    $ollama = @(
        "$root\tools\Ollama\ollama.exe",
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $ollama) { throw "Ollama not found." }

    $env:OLLAMA_MODELS = "$root\models\ollama"
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    if (-not (Wait-Port 11434 60)) { throw "Ollama failed." }
}

if (-not (Port-Is-Open 8010)) {
    $gatewayRoot = "$root\services\model-gateway"
    $gatewayPython = "$gatewayRoot\.venv\Scripts\python.exe"

    $old = @{}
    $vars = if ($providerHubReady) {
        $providerHubKey = Get-ProviderHubKey
        @{
            BARMANA_BASE_URL = "http://127.0.0.1:8020/v1"
            BARMANA_API_KEY = $providerHubKey
            BARMANA_AUTH_MODE = "bearer"
            BARMANA_MODELS_PATH = "/models"
            BARMANA_CHAT_PATH = "/chat/completions"
            DEFAULT_MODEL = "auto"
            FALLBACK_MODELS = ""
            MAX_FALLBACK_ATTEMPTS = "1"
            READ_TIMEOUT_SECONDS = "300"
            NO_PROXY = "localhost,127.0.0.1,::1"
        }
    } else {
        @{
            BARMANA_BASE_URL = "http://127.0.0.1:11434/v1"
            BARMANA_API_KEY = "ollama"
            BARMANA_AUTH_MODE = "bearer"
            BARMANA_MODELS_PATH = "/models"
            BARMANA_CHAT_PATH = "/chat/completions"
            DEFAULT_MODEL = "qwen2.5-coder:3b"
            FALLBACK_MODELS = ""
            MAX_FALLBACK_ATTEMPTS = "1"
            READ_TIMEOUT_SECONDS = "300"
            NO_PROXY = "localhost,127.0.0.1,::1"
        }
    }

    try {
        foreach ($name in $vars.Keys) {
            $item = Get-Item "Env:\$name" -ErrorAction SilentlyContinue
            $old[$name] = if ($item) { $item.Value } else { $null }
            Set-Item "Env:\$name" $vars[$name]
        }

        Start-Process `
            -FilePath $gatewayPython `
            -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8010 --workers 1" `
            -WorkingDirectory $gatewayRoot `
            -WindowStyle Hidden
    }
    finally {
        foreach ($name in $vars.Keys) {
            if ($null -eq $old[$name]) {
                Remove-Item "Env:\$name" -ErrorAction SilentlyContinue
            } else {
                Set-Item "Env:\$name" $old[$name]
            }
        }
    }

    if (-not (Wait-Port 8010 60)) { throw "Model Gateway failed." }
}

if (-not (Port-Is-Open 8011)) {
    $agentRoot = "$root\services\local-agent"
    Start-Process `
        -FilePath "$agentRoot\.venv\Scripts\python.exe" `
        -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8011 --workers 1" `
        -WorkingDirectory $agentRoot `
        -WindowStyle Hidden

    if (-not (Wait-Port 8011 60)) { throw "Local Agent failed." }
}

if (-not (Port-Is-Open 8012)) {
    $orchestratorRoot = "$root\services\orchestrator"
    Start-Process `
        -FilePath "$orchestratorRoot\.venv\Scripts\python.exe" `
        -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8012 --workers 1" `
        -WorkingDirectory $orchestratorRoot `
        -WindowStyle Hidden

    if (-not (Wait-Port 8012 60)) { throw "Orchestrator failed." }
}

if (-not (Port-Is-Open 5175)) {
    $uiRoot = "$root\apps\control-center"
    Start-Process `
        -FilePath "npm.cmd" `
        -ArgumentList "run dev -- --host 127.0.0.1 --port 5175" `
        -WorkingDirectory $uiRoot `
        -WindowStyle Hidden

    if (-not (Wait-Port 5175 60)) { throw "Control Center failed." }
}

$desktopRoot = "$root\apps\desktop"
$desktopEntry = "$desktopRoot\dist\index.html"
if (-not (Test-Path $desktopEntry)) {
    npm.cmd run build --prefix $desktopRoot
    if ($LASTEXITCODE -ne 0) { throw "Desktop build failed." }
}

# The supported surface is the packaged Electron control center.  The web UI
# remains available on port 5175 for diagnostics, but startup no longer
# silently falls back to opening a browser tab.
Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList @("--prefix", $desktopRoot, "start") `
    -WorkingDirectory $desktopRoot `
    -WindowStyle Hidden

Write-Host ""
Write-Host "AI ENGINEER IS RUNNING" -ForegroundColor Green
Write-Host "UI:           http://127.0.0.1:5175"
Write-Host "Orchestrator: http://127.0.0.1:8012"
Write-Host "Local Agent:  http://127.0.0.1:8011"
Write-Host "Gateway:      http://127.0.0.1:8010"
if ($providerHubReady) {
    Write-Host "Provider Hub: http://127.0.0.1:8020 (Codex Responses + OpenAI-compatible proxy)"
}
Write-Host "Ollama:       http://127.0.0.1:11434"
