#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$GatewayPort = 8010
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$baseUrl = "http://127.0.0.1:$GatewayPort"

$health = Invoke-RestMethod `
    -Method Get `
    -Uri "$baseUrl/health" `
    -TimeoutSec 10

Write-Host "Gateway version: $($health.version)" -ForegroundColor Green

$models = Invoke-RestMethod `
    -Method Get `
    -Uri "$baseUrl/v1/models?refresh=true" `
    -TimeoutSec 60

Write-Host "Models: $(@($models.data).Count)"

$body = @{
    messages = @(
        @{
            role = "user"
            content = "Reply only with OK"
        }
    )
    temperature = 0
    max_tokens = 16
    project_id = "phase-1"
    task_id = "headless-smoke-test"
    agent_id = "system-test"
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod `
    -Method Post `
    -Uri "$baseUrl/v1/chat/completions" `
    -ContentType "application/json; charset=utf-8" `
    -Body ([Text.Encoding]::UTF8.GetBytes($body)) `
    -TimeoutSec 360

Write-Host "SUCCESS" -ForegroundColor Green
Write-Host "Model: $($response.gateway.selected_model)"
Write-Host "Response: $($response.choices[0].message.content)"