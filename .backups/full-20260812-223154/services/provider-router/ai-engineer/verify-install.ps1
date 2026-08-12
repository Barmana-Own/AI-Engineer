#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$serviceRoot = [IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..")
)

$required = @(
    "LICENSE",
    "package.json",
    "package-lock.json",
    "server",
    "client",
    "node_modules",
    ".env",
    "ai-engineer\upstream-lock.json"
)

$missing = @(
    $required |
        ForEach-Object { Join-Path $serviceRoot $_ } |
        Where-Object { -not (Test-Path -LiteralPath $_) }
)

if ($missing.Count -gt 0) {
    throw "Provider Router validation failed: $($missing -join ', ')"
}

Write-Host "Vendored Provider Router files are complete." -ForegroundColor Green