#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8010
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

$BaseUrl = "http://127.0.0.1:$Port"

Write-Host "1) Testing health..." -ForegroundColor Cyan
$Health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health" -TimeoutSec 10
$Health | ConvertTo-Json -Depth 6

Write-Host ""
Write-Host "2) Testing model catalog..." -ForegroundColor Cyan
$Models = Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/v1/models" `
    -TimeoutSec 90

Write-Host "Model count: $($Models.data.Count)"
Write-Host "Cached: $($Models.cached)"
Write-Host "Stale: $($Models.stale)"

Write-Host ""
Write-Host "3) Testing chat with configured default and automatic fallback..." -ForegroundColor Cyan

$ChatBody = @{
    messages = @(
        @{
            role = "user"
            content = "Reply only with OK"
        }
    )
    temperature = 0
    max_tokens = 16
    project_id = "phase-1"
    task_id = "smoke-test"
    agent_id = "system-test"
} | ConvertTo-Json -Depth 10

try {
    $Chat = Invoke-RestMethod `
        -Method Post `
        -Uri "$BaseUrl/v1/chat/completions" `
        -ContentType "application/json; charset=utf-8" `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($ChatBody)) `
        -TimeoutSec 300

    Write-Host ""
    Write-Host "Chat succeeded." -ForegroundColor Green
    Write-Host "Selected model: $($Chat.gateway.selected_model)"
    Write-Host "Attempted models: $($Chat.gateway.attempted_models -join ', ')"
    Write-Host "Fallback used: $($Chat.gateway.fallback_used)"
    Write-Host "Latency: $($Chat.gateway.latency_ms) ms"
    Write-Host "Response: $($Chat.choices[0].message.content)"
}
catch {
    Write-Host ""
    Write-Host "Chat did not succeed." -ForegroundColor Red

    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message
    }
    else {
        Write-Host $_.Exception.Message
    }

    Write-Host ""
    Write-Host "The health and model tests may still be successful."
}

Write-Host ""
Write-Host "4) Reading local usage summary..." -ForegroundColor Cyan
$Usage = Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/v1/usage/summary" `
    -TimeoutSec 10

$Usage | ConvertTo-Json -Depth 10
