#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Root = "",
    [string]$OutputDirectory = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$Root = [System.IO.Path]::GetFullPath($Root)
if (-not (Test-Path -LiteralPath $Root -PathType Container)) { throw "Release root does not exist: $Root" }

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $Root "release"
}
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$projectName = Split-Path -Leaf $Root
$stage = Join-Path $OutputDirectory ".stage-$timestamp"
$archive = Join-Path $OutputDirectory "$projectName-$timestamp.zip"
New-Item -ItemType Directory -Force -Path $stage | Out-Null

$excludedDirectoryNames = @(
    ".git", ".backups", "backups", "node_modules", ".venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage", "dist", "build",
    "runtime", "logs", "workspaces", "tmp", "models", "data", "Ollama", ".cache", ".turbo", ".next"
)
$excludedFileNames = @(
    ".env", ".env.local", ".env.development.local", ".env.test.local",
    ".env.production", ".env.production.local"
)
$excludedSuffixes = @(".db", ".sqlite", ".sqlite3", ".log", ".bak", ".tmp")
$credentialPattern = '(?i)(password|passwd|secret|token|credential|private[-_ ]?key|service[-_ ]account)'

function Test-IncludedFile([System.IO.FileInfo]$File) {
    $relative = $File.FullName.Substring($Root.Length).TrimStart([char[]]@('\','/'))
    $segments = $relative -split '[\\/]'
    if (@($segments | Where-Object { $excludedDirectoryNames -contains $_ }).Count -gt 0) { return $false }
    if ($excludedFileNames -contains $File.Name) { return $false }
    if ($File.Name -match $credentialPattern -and $File.Extension -in @('.json','.yaml','.yml','.txt','.pem','.key','.p12')) { return $false }
    if ($excludedSuffixes -contains $File.Extension.ToLowerInvariant()) { return $false }
    return $true
}

$files = [System.Collections.Generic.List[System.IO.FileInfo]]::new()
$directories = [System.Collections.Generic.Stack[System.IO.DirectoryInfo]]::new()
$directories.Push((Get-Item -LiteralPath $Root))
while ($directories.Count -gt 0) {
    $directory = $directories.Pop()
    foreach ($childDirectory in Get-ChildItem -LiteralPath $directory.FullName -Directory -Force) {
        if ($excludedDirectoryNames -notcontains $childDirectory.Name) { $directories.Push($childDirectory) }
    }
    foreach ($file in Get-ChildItem -LiteralPath $directory.FullName -File -Force) {
        if (Test-IncludedFile $file) { $files.Add($file) }
    }
}
foreach ($file in $files) {
    $relative = $file.FullName.Substring($Root.Length).TrimStart([char[]]@('\','/'))
    $destination = Join-Path $stage $relative
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
}

$manifest = @"
# AI Engineer sanitized release snapshot

- Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')
- Source root: repository source only
- Secrets and runtime state were excluded.

Excluded categories: Git metadata, backups, dependency directories, virtual environments, caches, build output, local databases, logs, workspaces, temporary files, local environment files, and credential/private-key-like files.

Install dependencies from the preserved package manifests and lockfiles before starting services.
"@
Write-Utf8 (Join-Path $stage "EXPORT-MANIFEST.md") $manifest
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $archive -CompressionLevel Optimal
$hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
Remove-Item -LiteralPath $stage -Recurse -Force
Write-Output "ARCHIVE=$archive"
Write-Output "SHA256=$hash"
Write-Output "FILES=$(@($files).Count)"