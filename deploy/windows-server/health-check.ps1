#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Chat,
    [string]$BaseUrl = "https://devoria.ir"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RequiredSecret([string]$Name) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) { throw "$Name is required for authenticated proxy checks." }
    return $value
}

function Invoke-JsonCheck([string]$Name, [string]$Url, [string]$ExpectedService, [hashtable]$Headers = @{}) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -Headers $Headers -TimeoutSec 20
        if ($response.StatusCode -ne 200) { throw "HTTP $($response.StatusCode)" }
        $payload = $response.Content | ConvertFrom-Json
        if ($payload.status -ne "ok") { throw "unexpected status: $($payload.status)" }
        if ($ExpectedService -and $payload.service -notlike "*$ExpectedService*") {
            throw "unexpected service identity: $($payload.service)"
        }
        Write-Host ("PASS {0} ({1})" -f $Name, $response.StatusCode) -ForegroundColor Green
        return $payload
    }
    catch {
        Write-Host ("FAIL {0}: {1}" -f $Name, $_.Exception.Message) -ForegroundColor Red
        throw
    }
}

function Invoke-HttpCheck([string]$Name, [string]$Url, [hashtable]$Headers = @{}) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -Headers $Headers -TimeoutSec 20
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) { throw "HTTP $($response.StatusCode)" }
        Write-Host ("PASS {0} ({1})" -f $Name, $response.StatusCode) -ForegroundColor Green
    }
    catch {
        Write-Host ("FAIL {0}: {1}" -f $Name, $_.Exception.Message) -ForegroundColor Red
        throw
    }
}

function Invoke-GatewayModelsCheck([string]$Name, [string]$Url, [hashtable]$Headers = @{}) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -Headers $Headers -TimeoutSec 20
        if ($response.StatusCode -ne 200) { throw "HTTP $($response.StatusCode)" }
        $payload = $response.Content | ConvertFrom-Json
        if (-not $payload.provider -or -not $payload.default_model) {
            throw "gateway model catalog response is missing provider/default_model."
        }
        Write-Host ("PASS {0} ({1})" -f $Name, $response.StatusCode) -ForegroundColor Green
        return $payload
    }
    catch {
        Write-Host ("FAIL {0}: {1}" -f $Name, $_.Exception.Message) -ForegroundColor Red
        throw
    }
}

function Invoke-CapabilitiesCheck([string]$Name, [string]$Url, [hashtable]$Headers = @{}) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -Headers $Headers -TimeoutSec 20
        if ($response.StatusCode -ne 200) { throw "HTTP $($response.StatusCode)" }
        $payload = $response.Content | ConvertFrom-Json
        if ($payload.service -notlike "*Orchestrator*" -or $payload.workspace_guarded -ne $true -or $payload.mutation_requires_checkpoint -ne $true) {
            throw "orchestrator capabilities response failed safety assertions."
        }
        Write-Host ("PASS {0} ({1})" -f $Name, $response.StatusCode) -ForegroundColor Green
        return $payload
    }
    catch {
        Write-Host ("FAIL {0}: {1}" -f $Name, $_.Exception.Message) -ForegroundColor Red
        throw
    }
}

$controlToken = Get-RequiredSecret "AI_ENGINE_CONTROL_PLANE_TOKEN"
$gatewayToken = Get-RequiredSecret "AI_ENGINE_GATEWAY_TOKEN"
$controlHeaders = @{ "X-AI-Engine-Token" = $controlToken }
$gatewayHeaders = @{ "X-AI-Engine-Token" = $gatewayToken }

Invoke-HttpCheck "Ollama" "http://127.0.0.1:11434/api/version"
Invoke-JsonCheck "Model Gateway" "http://127.0.0.1:8010/health" "Gateway" | Out-Null
Invoke-JsonCheck "Local Agent" "http://127.0.0.1:8011/health" "Local Agent" | Out-Null
$orchestrator = Invoke-JsonCheck "Orchestrator" "http://127.0.0.1:8012/health" "Orchestrator"
Invoke-HttpCheck "Control Center" "$BaseUrl/"
Invoke-GatewayModelsCheck "Gateway Proxy" "$BaseUrl/api/gateway/v1/runtime/models" $gatewayHeaders | Out-Null
Invoke-JsonCheck "Orchestrator Proxy" "$BaseUrl/api/orchestrator/health" "Orchestrator" | Out-Null
Invoke-CapabilitiesCheck "Authenticated Orchestrator" "$BaseUrl/api/orchestrator/capabilities" $controlHeaders | Out-Null

if ($Chat) {
    $body = @{
        messages = @(@{ role = "user"; content = "Reply only with OK" })
        temperature = 0
        max_tokens = 16
        project_id = "server-smoke-test"
        task_id = "server-smoke-test"
        agent_id = "system-test"
    } | ConvertTo-Json -Depth 8
    $response = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/gateway/v1/chat/completions" -Headers $gatewayHeaders -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 600
    if (-not $response.gateway.selected_model) { throw "Gateway chat response did not include selected_model." }
    Write-Host "PASS Chat model=$($response.gateway.selected_model)" -ForegroundColor Green
}

Write-Host "All deployment health checks passed." -ForegroundColor Green
