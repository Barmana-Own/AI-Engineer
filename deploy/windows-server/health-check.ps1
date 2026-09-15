#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Chat
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$checks = @(
    @{ Name = "Ollama"; Url = "http://127.0.0.1:11434/api/version" },
    @{ Name = "Model Gateway"; Url = "http://127.0.0.1:8010/health/ready" },
    @{ Name = "Local Agent"; Url = "http://127.0.0.1:8011/health" },
    @{ Name = "Orchestrator"; Url = "http://127.0.0.1:8012/health" },
    @{ Name = "Control Center"; Url = "http://devoria.ir/" },
    @{ Name = "Gateway Proxy"; Url = "http://devoria.ir/api/gateway/v1/runtime/models" },
    @{ Name = "Orchestrator Proxy"; Url = "http://devoria.ir/api/orchestrator/health" }
)

foreach ($check in $checks) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $check.Url -TimeoutSec 20
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) { throw "HTTP $($response.StatusCode)" }
        Write-Host ("PASS {0} ({1})" -f $check.Name, $response.StatusCode) -ForegroundColor Green
    }
    catch {
        Write-Host ("FAIL {0}: {1}" -f $check.Name, $_.Exception.Message) -ForegroundColor Red
        exit 1
    }
}

if ($Chat) {
    $body = @{
        messages = @(
            @{
                role = "user"
                content = "Reply only with OK"
            }
        )
        temperature = 0
        max_tokens = 16
        project_id = "server-smoke-test"
        task_id = "server-smoke-test"
        agent_id = "system-test"
    } | ConvertTo-Json -Depth 8

    $response = Invoke-RestMethod -Method Post -Uri "http://devoria.ir/api/gateway/v1/chat/completions" -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 600
    Write-Host "PASS Chat model=$($response.gateway.selected_model)" -ForegroundColor Green
}