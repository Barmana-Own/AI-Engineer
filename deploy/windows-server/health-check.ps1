#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$PublicBaseUrl = "https://devoria.ir",
    [switch]$Chat
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$checks = @(
    @{ Name = "Ollama"; Url = "http://127.0.0.1:11434/api/version"; ExpectedField = "version"; ExpectedValue = $null },
    @{ Name = "Model Gateway"; Url = "http://127.0.0.1:8010/health/ready"; ExpectedField = "status"; ExpectedValue = "ready" },
    @{ Name = "Local Agent"; Url = "http://127.0.0.1:8011/health"; ExpectedField = "status"; ExpectedValue = "ok" },
    @{ Name = "Orchestrator"; Url = "http://127.0.0.1:8012/health"; ExpectedField = "status"; ExpectedValue = "ok" },
    @{ Name = "Control Center"; Url = ($PublicBaseUrl.TrimEnd('/') + "/"); ExpectedField = "html"; ExpectedValue = $null },
    @{ Name = "Orchestrator Proxy"; Url = ($PublicBaseUrl.TrimEnd('/') + "/api/orchestrator/health"); ExpectedField = "service"; ExpectedValue = $null }
)

function Get-PropertyValue($Object, [string]$Name) {
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

foreach ($check in $checks) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $check.Url -TimeoutSec 20
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) { throw "HTTP $($response.StatusCode)" }
        if ($check.ExpectedField -eq "html") {
            if ($response.Content -notmatch '(?i)<html|<!doctype') { throw "response is not HTML" }
        } else {
            $payload = $response.Content | ConvertFrom-Json
            $value = Get-PropertyValue $payload $check.ExpectedField
            if ([string]::IsNullOrWhiteSpace([string]$value)) { throw "missing identity field $($check.ExpectedField)" }
            if ($null -ne $check.ExpectedValue -and $value -ne $check.ExpectedValue) { throw "expected $($check.ExpectedField)=$($check.ExpectedValue), received $value" }
        }
        Write-Host ("PASS {0} ({1})" -f $check.Name, $response.StatusCode) -ForegroundColor Green
    }
    catch {
        Write-Host ("FAIL {0}: {1}" -f $check.Name, $_.Exception.Message) -ForegroundColor Red
        exit 1
    }
}

if ($Chat) {
    $body = @{
        messages = @(@{ role = "user"; content = "Reply only with OK" })
        temperature = 0
        max_tokens = 16
        project_id = "server-smoke-test"
        task_id = "server-smoke-test"
        agent_id = "system-test"
    } | ConvertTo-Json -Depth 8
    $response = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8010/v1/chat/completions" -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 600
    if ($null -eq $response.gateway.selected_model) { throw "Gateway chat response did not include selected_model" }
    Write-Host "PASS Chat" -ForegroundColor Green
}