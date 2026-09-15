#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ports = 5175, 8012, 8011, 8010, 8020, 11434

foreach ($port in $ports) {
    $connection = Get-NetTCPConnection `
        -LocalPort $port `
        -State Listen `
        -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if (-not $connection) { continue }

    $process = Get-CimInstance Win32_Process `
        -Filter "ProcessId=$($connection.OwningProcess)" `
        -ErrorAction SilentlyContinue

    if ($process -and $process.Name -in @("node.exe", "python.exe", "ollama.exe")) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped port $port PID $($process.ProcessId)"
    }
}

Write-Host "AI Engineer services stopped." -ForegroundColor Green
