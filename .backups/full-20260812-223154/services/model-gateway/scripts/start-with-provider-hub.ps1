#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$GatewayPort = 8010
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    chcp 65001 | Out-Null
    [Console]::InputEncoding = New-Object Text.UTF8Encoding($false)
    [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {
}

$serviceRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $serviceRoot ".venv\Scripts\python.exe"
$routerBaseUrl = "http://127.0.0.1:8020/v1"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Python virtual environment is missing."
}

$routerPort = Get-NetTCPConnection `
    -LocalPort 8020 `
    -State Listen `
    -ErrorAction SilentlyContinue |
    Select-Object -First 1

if (-not $routerPort) {
    throw "Provider Hub is not running on port 8020."
}

$secureKey = Read-Host "Unified local Provider Hub key" -AsSecureString
$bstr = [IntPtr]::Zero
$plainKey = $null

try {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)

    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw "Unified key cannot be empty."
    }

    $headers = @{
        Authorization = "Bearer $plainKey"
        Accept = "application/json"
    }

    $catalog = Invoke-RestMethod `
        -Method Get `
        -Uri "$routerBaseUrl/models" `
        -Headers $headers `
        -TimeoutSec 30

    $models = @(
        $catalog.data |
            Where-Object {
                $_.id -and
                $_.id -notmatch "embedding|image|audio|speech|tts|whisper|moderation"
            } |
            Select-Object -ExpandProperty id -Unique |
            Select-Object -First 4
    )

    if ($models.Count -eq 0) {
        throw "Provider Hub returned no usable models."
    }

    $env:BARMANA_BASE_URL = $routerBaseUrl
    $env:BARMANA_API_KEY = $plainKey
    $env:BARMANA_AUTH_MODE = "bearer"
    $env:BARMANA_MODELS_PATH = "/models"
    $env:BARMANA_CHAT_PATH = "/chat/completions"
    $env:DEFAULT_MODEL = [string]$models[0]
    $env:FALLBACK_MODELS = (@($models | Select-Object -Skip 1) -join ",")
    $env:MAX_FALLBACK_ATTEMPTS = "$($models.Count)"
    $env:GATEWAY_HOST = "127.0.0.1"
    $env:GATEWAY_PORT = "$GatewayPort"
    $env:READ_TIMEOUT_SECONDS = "120"

    Set-Location $serviceRoot

    Write-Host ""
    Write-Host "AI Engineer Model Gateway" -ForegroundColor Green
    Write-Host "Gateway: http://127.0.0.1:$GatewayPort"
    Write-Host "Provider Hub: $routerBaseUrl"
    Write-Host "Default model: $($models[0])"
    Write-Host "Press Ctrl+C to stop."
    Write-Host ""

    & $venvPython `
        -m uvicorn `
        app.main:app `
        --host 127.0.0.1 `
        --port $GatewayPort `
        --workers 1
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