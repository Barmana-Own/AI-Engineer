#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Root = ""
    [string]$TaskUser = "SYSTEM"
    [string]$TaskPassword = "",
    [switch]$StartNow
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
$taskName = "AI Engineer Server"
$startScript = Join-Path $Root "deploy\windows-server\start-ai-engineer-server.ps1"
$logRoot = Join-Path $Root "logs\server"

if (-not (Test-Path -LiteralPath $startScript)) {
    throw "Deployment start script is missing: $startScript"
}

New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

$powerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $startScript + '" -Root "' + $Root + '"'
$action = New-ScheduledTaskAction -Execute $powerShell -Argument $arguments -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -AtStartup
if ($TaskUser -ieq "SYSTEM") {
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Starts the AI Engineer local services after Windows startup." -Force | Out-Null
}
else {
    if ([string]::IsNullOrWhiteSpace($TaskPassword)) {
        throw "TaskPassword is required when TaskUser is not SYSTEM."
    }
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -User $TaskUser -Password $TaskPassword -RunLevel Highest -Settings $settings -Description "Starts the AI Engineer local services after Windows startup." -Force | Out-Null
}

if ($StartNow) {
    Start-ScheduledTask -TaskName $taskName
}

$task = Get-ScheduledTask -TaskName $taskName
Write-Host "Registered task: $($task.TaskName)"
Write-Host "Run as: $($task.Principal.UserId)"
Write-Host "Startup mode: $($task.State)"
if ($StartNow) {
    Write-Host "Start requested."
}