#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Root = "",
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
$taskLog = Join-Path $logRoot "startup-task.log"

if (-not (Test-Path -LiteralPath $startScript)) {
    throw "Deployment start script is missing: $startScript"
}

New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

$powerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$arguments = '/d /c ""' + $powerShell + '" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $startScript + '" -Root "' + $Root + '" > "' + $taskLog + '" 2>&1"'
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Starts the AI Engineer local services after Windows startup." -Force | Out-Null

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