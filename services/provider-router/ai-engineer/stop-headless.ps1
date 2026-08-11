#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$serviceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))

$processes = @(
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq "node.exe" -and
            $_.CommandLine -and
            (
                $_.CommandLine -like "*$serviceRoot*" -or
                $_.CommandLine -like "*server\dist\index.js*"
            )
        }
)

if ($processes.Count -eq 0) {
    Write-Host "Provider Hub is not running." -ForegroundColor Yellow
    exit 0
}

foreach ($process in $processes) {
    Write-Host "Stopping Provider Hub PID $($process.ProcessId)..."
    Stop-Process -Id $process.ProcessId -Force
}

Write-Host "Provider Hub stopped." -ForegroundColor Green