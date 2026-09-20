#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Root = "",
    [string]$OutputPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = if (-not [string]::IsNullOrWhiteSpace($env:AI_ENGINE_PROJECT_ROOT)) {
        $env:AI_ENGINE_PROJECT_ROOT
    } else {
        (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    }
}
$Root = (Resolve-Path -LiteralPath $Root).Path
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputPath = Join-Path $Root "artifacts\AI-Engineer-release-$stamp.zip"
}
$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$outputDirectory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-engineer-release-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

$excludedDirectories = @(
    ".git", ".venv", "venv", "node_modules", "vendor", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache", "coverage",
    "htmlcov", ".next", ".nuxt", ".vite", "out", "target", "logs",
    "data", "workspaces", "backups", ".backups", "artifacts", "tmp", "temp",
    "docker-data", "postgres-data", "redis-data", "models"
)

try {
    Get-ChildItem -LiteralPath $Root -Recurse -File -Force |
        Where-Object {
            $relative = $_.FullName.Substring($Root.Length).TrimStart('\', '/')
            $parts = $relative -split '[\\/]'
            $excluded = $false
            foreach ($part in $parts) {
                if ($excludedDirectories -contains $part) { $excluded = $true; break }
            }
            if ($excluded) { return $false }
            if ($_.Name -match '^\.env($|\.)' -and $_.Name -ne '.env.example') { return $false }
            if ($_.Name -match '(?i)(^|\.)credentials?($|\.|_)|(^|\.)secrets?($|\.|_)') { return $false }
            if ($_.Extension -match '(?i)^\.(db|sqlite|sqlite3|dump|bak|backup|zip|7z|tar|gz|log|tmp|temp|pem|key|pfx|p12)$') { return $false }
            return $true
        } |
        ForEach-Object {
            $relative = $_.FullName.Substring($Root.Length).TrimStart('\', '/')
            $destination = Join-Path $tempRoot $relative
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
        }

    $suspicious = Get-ChildItem -LiteralPath $tempRoot -Recurse -File -Force |
        Where-Object { ((($_.Name -match '(?i)^\.env($|\.)') -and $_.Name -ne '.env.example') -or ($_.Name -match '(?i)(credentials?|secrets?|private-key|service-account)')) }
    if ($suspicious) {
        throw "Sanitized release contains a forbidden secret-like file: $($suspicious.FullName -join ', ')"
    }

    # Scan configuration/data files for high-confidence credential signatures.
    # Source and test files may legitimately contain redaction fixtures.
    $suspiciousContent = Get-ChildItem -LiteralPath $tempRoot -Recurse -File -Force |
        Where-Object {
            if ($_.Name -eq '.env.example' -or $_.Length -gt 2MB) { return $false }
            if ($_.Name -match '(?i)(package-lock|yarn.lock|pnpm-lock)') { return $false }
            if ($_.Extension -notmatch '(?i)^\.(json|ya?ml|toml|ini|cfg|conf)$') { return $false }
            $content = [System.IO.File]::ReadAllText($_.FullName)
            return $content -match '(?i)-----BEGIN (?:RSA|EC|OPENSSH|DSA|PRIVATE) PRIVATE KEY-----|(?:AKIA|ASIA)[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|xox[baprs]-[A-Za-z0-9-]{20,}|sk-[A-Za-z0-9]{32,}|(?:postgres|mysql|mssql|redis|mongodb)(?:\+[^:]+)?://[^/\s:]+:[^@\s]{8,}@'
        }
    if ($suspiciousContent) {
        throw "Sanitized release contains a high-confidence credential signature: $($suspiciousContent.FullName -join ', ')"
    }

    if (Test-Path -LiteralPath $OutputPath) { Remove-Item -LiteralPath $OutputPath -Force }
    Compress-Archive -Path (Join-Path $tempRoot '*') -DestinationPath $OutputPath -CompressionLevel Optimal
    Write-Host "Release archive: $OutputPath" -ForegroundColor Green
    Write-Host "Excluded dependency, cache, runtime-data, and secret-like files by policy."
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
