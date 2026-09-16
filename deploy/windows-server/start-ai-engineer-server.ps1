#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Root = "",
    [switch]$PullModel
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Root)) {
    $scriptRoot = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($scriptRoot)) {
        $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    }
    if ([string]::IsNullOrWhiteSpace($scriptRoot)) {
        throw "Could not resolve the deployment script directory. Pass -Root explicitly."
    }
    $Root = (Resolve-Path (Join-Path $scriptRoot "..\..")).Path
}

$Root = [System.IO.Path]::GetFullPath($Root)
$Model = "qwen3:8b"
$LogRoot = Join-Path $Root "logs\server"
$DataRoot = Join-Path $Root "data"
$WorkspaceRoot = Join-Path $Root "workspaces"
$WebRoot = Join-Path $Root "apps\control-center\dist"

New-Item -ItemType Directory -Force -Path $LogRoot, $DataRoot, $WorkspaceRoot | Out-Null

function Port-Is-Open([int]$Port) {
    return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Wait-Port([int]$Port, [int]$Seconds = 60) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Port-Is-Open $Port) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Wait-Http([string]$Url, [int]$Seconds = 60) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { return $true }
        }
        catch {
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Set-ChildEnvironment([hashtable]$Values, [scriptblock]$Action) {
    $oldValues = @{}
    foreach ($name in $Values.Keys) {
        $item = Get-Item "Env:\$name" -ErrorAction SilentlyContinue
        $oldValues[$name] = if ($item) { $item.Value } else { $null }
        Set-Item "Env:\$name" ([string]$Values[$name])
    }
    try {
        & $Action
    }
    finally {
        foreach ($name in $Values.Keys) {
            if ($null -eq $oldValues[$name]) { Remove-Item "Env:\$name" -ErrorAction SilentlyContinue }
            else { Set-Item "Env:\$name" $oldValues[$name] }
        }
    }
}

function Start-PythonService([string]$Name, [string]$Python, [string]$WorkingDirectory, [int]$Port, [string[]]$Arguments, [hashtable]$Environment) {
    if (-not (Test-Path -LiteralPath $Python)) { throw "$Name virtual environment is missing: $Python" }
    if (Port-Is-Open $Port) {
        if (-not (Wait-Http "http://127.0.0.1:$Port/health" 10)) { throw "$Name port $Port is occupied by an unhealthy process." }
        return
    }

    $stdout = Join-Path $LogRoot "$Name.out.log"
    $stderr = Join-Path $LogRoot "$Name.err.log"
    Set-ChildEnvironment $Environment {
        Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden | Out-Null
    }

    if (-not (Wait-Port $Port 60) -or -not (Wait-Http "http://127.0.0.1:$Port/health" 10)) {
        throw "$Name failed to become healthy. See $stderr"
    }
}

$Ollama = @(
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "$env:ProgramFiles\Ollama\ollama.exe",
    (Join-Path $Root "tools\Ollama\ollama.exe")
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not (Port-Is-Open 11434)) {
    if (-not $Ollama) { throw "Ollama is not listening and its executable was not found." }
    Start-Process -FilePath $Ollama -ArgumentList "serve" -WindowStyle Hidden | Out-Null
    if (-not (Wait-Port 11434 60)) { throw "Ollama failed to start." }
}

if (-not $Ollama) {
    $ollamaProcess = Get-Process -Name ollama -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($ollamaProcess) {
        $Ollama = (Get-CimInstance Win32_Process -Filter "ProcessId=$($ollamaProcess.Id)" -ErrorAction SilentlyContinue).ExecutablePath
    }
}

if ($PullModel -and $Ollama) {
    & $Ollama pull $Model
    if ($LASTEXITCODE -ne 0) { throw "Ollama could not pull $Model." }
}

$tags = Invoke-RestMethod -UseBasicParsing -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 30
if (-not (@($tags.models | Where-Object { $_.name -eq $Model }).Count)) {
    throw "Required Ollama model is not installed: $Model. Run with -PullModel."
}

$gatewayRoot = Join-Path $Root "services\model-gateway"
$agentRoot = Join-Path $Root "services\local-agent"
$orchestratorRoot = Join-Path $Root "services\orchestrator"

$gatewayEnvironment = @{
    APP_ENVIRONMENT = "production"
    GATEWAY_HOST = "127.0.0.1"
    GATEWAY_PORT = "8010"
    BARMANA_BASE_URL = "http://127.0.0.1:11434/v1"
    BARMANA_API_KEY = "ollama"
    BARMANA_AUTH_MODE = "bearer"
    BARMANA_MODELS_PATH = "/models"
    BARMANA_CHAT_PATH = "/chat/completions"
    DEFAULT_MODEL = $Model
    FALLBACK_MODELS = ""
    MAX_FALLBACK_ATTEMPTS = "1"
    READ_TIMEOUT_SECONDS = "600"
    NO_PROXY = "localhost,127.0.0.1,::1"
}

$agentEnvironment = @{
    ENVIRONMENT = "production"
    HOST = "127.0.0.1"
    PORT = "8011"
    WORKSPACE_ROOT = $WorkspaceRoot
    SELF_WORKSPACE_NAME = "ai-engineer"
    SELF_WORKSPACE_ROOT = $Root
    MANAGED_PROCESS_REGISTRY_PATH = Join-Path $DataRoot "local-agent\processes.json"
    MANAGED_PROCESS_LOG_ROOT = Join-Path $LogRoot "managed-processes"
}

$orchestratorEnvironment = @{
    ENVIRONMENT = "production"
    HOST = "127.0.0.1"
    PORT = "8012"
    MODEL_GATEWAY_URL = "http://127.0.0.1:8010"
    LOCAL_AGENT_URL = "http://127.0.0.1:8011"
    WORKSPACE_ROOT = $WorkspaceRoot
    SELF_WORKSPACE_NAME = "ai-engineer"
    SELF_WORKSPACE_ROOT = $Root
    ORCHESTRATOR_DB_PATH = Join-Path $DataRoot "orchestrator\orchestrator.db"
    AGENT_MODEL = $Model
    AUTONOMOUS_AGENT_MODEL = $Model
    AUTONOMOUS_MODE_ENABLED = "true"
    AUTONOMOUS_INTERVAL_MINUTES = "5"
    AUTONOMOUS_CYCLES_PER_RUN = "1"
    AUTONOMOUS_TASK_TIMEOUT_SECONDS = "900"
    AUTONOMOUS_MODEL_TIMEOUT_SECONDS = "600"
    AUTONOMOUS_RECONCILIATION_GRACE_SECONDS = "1800"
    AUTONOMOUS_READ_PARALLELISM = "2"
    AUTONOMOUS_SUBAGENTS = "implementer,verifier"
    AUTONOMOUS_MAX_SUBAGENTS = "2"
    AUTONOMOUS_INCLUDE_SECTION_SPECIALIST = "false"
    AUTONOMOUS_WORKSPACE = "ai-engineer"
    AUTONOMOUS_AUTO_PUSH = "true"
    AUTONOMOUS_REPO_ROOT = $Root
}

Start-PythonService "model-gateway" (Join-Path $gatewayRoot ".venv\Scripts\python.exe") $gatewayRoot 8010 @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010", "--workers", "1") $gatewayEnvironment
Start-PythonService "local-agent" (Join-Path $agentRoot ".venv\Scripts\python.exe") $agentRoot 8011 @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8011", "--workers", "1") $agentEnvironment
Start-PythonService "orchestrator" (Join-Path $orchestratorRoot ".venv\Scripts\python.exe") $orchestratorRoot 8012 @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8012", "--workers", "1") $orchestratorEnvironment

if (-not (Test-Path -LiteralPath (Join-Path $WebRoot "web.config"))) { throw "IIS web.config is missing from the control-center build: $WebRoot" }

Write-Host "AI Engineer server services are healthy." -ForegroundColor Green
Write-Host "Ollama model: $Model"
Write-Host "Control Center build: $WebRoot"
Write-Host "Public URL: http://devoria.ir"
