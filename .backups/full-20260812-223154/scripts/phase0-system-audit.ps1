#requires -Version 5.1
<#
.SYNOPSIS
  Safe, read-only system audit for AI-Engineer Phase 0.

.DESCRIPTION
  Detects Windows, CPU, RAM, GPU/VRAM, free disk space, PowerShell,
  VS Code, Git, Python, Node.js, npm, Docker Desktop, WSL, and XAMPP.

  This script:
  - Does NOT require Administrator access.
  - Does NOT install or remove anything.
  - Does NOT change Windows settings.
  - Does NOT initialize Git or create the project workspace.
  - Only writes report files beside this script.

.PARAMETER ProjectDrive
  Drive letter planned for the project. Default: F

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\phase0-system-audit.ps1 -ProjectDrive F
#>

[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z]$')]
    [string]$ProjectDrive = 'F'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Safely {
    param(
        [Parameter(Mandatory)]
        [scriptblock]$Action,
        $Fallback = $null
    )

    try {
        & $Action
    }
    catch {
        $Fallback
    }
}

function Get-CommandInfo {
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        [string[]]$VersionArguments = @('--version')
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $command) {
        return [ordered]@{
            installed = $false
            path      = $null
            version   = $null
        }
    }

    $version = Invoke-Safely {
        $output = & $command.Source @VersionArguments 2>&1
        ($output | Select-Object -First 1 | Out-String).Trim()
    }

    return [ordered]@{
        installed = $true
        path      = $command.Source
        version   = $version
    }
}

function Find-Xampp {
    $candidatePaths = @(
        'C:\xampp',
        'D:\xampp',
        'E:\xampp',
        'F:\xampp',
        'C:\Program Files\xampp',
        'C:\Program Files (x86)\xampp'
    )

    $foundPath = $candidatePaths |
        Where-Object { Test-Path -LiteralPath $_ } |
        Select-Object -First 1

    if (-not $foundPath) {
        $uninstallRoots = @(
            'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
            'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
            'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
        )

        $entry = Invoke-Safely {
            Get-ItemProperty $uninstallRoots -ErrorAction SilentlyContinue |
                Where-Object { $_.DisplayName -match 'XAMPP' } |
                Select-Object -First 1
        }

        if ($entry) {
            $foundPath = $entry.InstallLocation
        }
    }

    return [ordered]@{
        installed = [bool]$foundPath
        path      = $foundPath
    }
}

function Convert-BytesToGB {
    param([double]$Bytes)

    if ($Bytes -le 0) {
        return $null
    }

    return [math]::Round($Bytes / 1GB, 2)
}

$driveLetter = $ProjectDrive.ToUpperInvariant()
$driveId = "${driveLetter}:"
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($scriptDirectory)) {
    $scriptDirectory = (Get-Location).Path
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$jsonReportPath = Join-Path $scriptDirectory "phase0-system-report-$timestamp.json"
$textReportPath = Join-Path $scriptDirectory "phase0-system-report-$timestamp.txt"

$computerSystem = Get-CimInstance Win32_ComputerSystem
$operatingSystem = Get-CimInstance Win32_OperatingSystem
$processor = Get-CimInstance Win32_Processor | Select-Object -First 1
$videoControllers = @(Get-CimInstance Win32_VideoController)
$logicalDisk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$driveId'" -ErrorAction SilentlyContinue

$gpuInfo = @(
    foreach ($gpu in $videoControllers) {
        [ordered]@{
            name              = $gpu.Name
            adapterRamGB      = Convert-BytesToGB ([double]$gpu.AdapterRAM)
            driverVersion     = $gpu.DriverVersion
            videoMode         = $gpu.VideoModeDescription
            note              = 'AdapterRAM may be unavailable or approximate on some Windows/GPU drivers.'
        }
    }
)

$pythonInfo = Get-CommandInfo -Name 'python' -VersionArguments @('--version')
if (-not $pythonInfo.installed) {
    $pythonInfo = Get-CommandInfo -Name 'py' -VersionArguments @('--version')
}

$dockerCli = Get-CommandInfo -Name 'docker' -VersionArguments @('--version')
$dockerDesktopPaths = @(
    "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
    "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
)
$dockerDesktopPath = $dockerDesktopPaths |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1

$wslCommand = Get-Command 'wsl.exe' -ErrorAction SilentlyContinue
$wslStatus = $null
$wslDistributions = @()
if ($wslCommand) {
    $wslStatus = Invoke-Safely {
        ((& wsl.exe --status 2>&1) | Out-String).Trim()
    }
    $wslDistributions = Invoke-Safely {
        @(& wsl.exe --list --quiet 2>$null | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    } @()
}

$report = [ordered]@{
    audit = [ordered]@{
        generatedAt       = (Get-Date).ToString('o')
        projectRoot       = "${driveId}\AI-Engineer"
        safeReadOnlyAudit = $true
        administrator     = ([Security.Principal.WindowsPrincipal]::new(
            [Security.Principal.WindowsIdentity]::GetCurrent()
        )).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    }
    system = [ordered]@{
        computerName       = $env:COMPUTERNAME
        manufacturer       = $computerSystem.Manufacturer
        model              = $computerSystem.Model
        windowsCaption     = $operatingSystem.Caption
        windowsVersion     = $operatingSystem.Version
        windowsBuild       = $operatingSystem.BuildNumber
        architecture       = $operatingSystem.OSArchitecture
        powershellVersion  = $PSVersionTable.PSVersion.ToString()
        totalRamGB         = [math]::Round(([double]$computerSystem.TotalPhysicalMemory / 1GB), 2)
        availableRamGB     = [math]::Round(([double]$operatingSystem.FreePhysicalMemory * 1KB / 1GB), 2)
    }
    cpu = [ordered]@{
        name              = $processor.Name.Trim()
        physicalCores     = $processor.NumberOfCores
        logicalProcessors = $processor.NumberOfLogicalProcessors
        maxClockMHz       = $processor.MaxClockSpeed
    }
    gpu = $gpuInfo
    projectDrive = if ($logicalDisk) {
        [ordered]@{
            exists      = $true
            drive       = $driveId
            volumeName  = $logicalDisk.VolumeName
            fileSystem  = $logicalDisk.FileSystem
            totalGB     = Convert-BytesToGB ([double]$logicalDisk.Size)
            freeGB      = Convert-BytesToGB ([double]$logicalDisk.FreeSpace)
        }
    } else {
        [ordered]@{
            exists      = $false
            drive       = $driveId
            volumeName  = $null
            fileSystem  = $null
            totalGB     = $null
            freeGB      = $null
        }
    }
    tools = [ordered]@{
        vscode = Get-CommandInfo -Name 'code' -VersionArguments @('--version')
        git = Get-CommandInfo -Name 'git' -VersionArguments @('--version')
        python = $pythonInfo
        node = Get-CommandInfo -Name 'node' -VersionArguments @('--version')
        npm = Get-CommandInfo -Name 'npm' -VersionArguments @('--version')
        dockerCli = $dockerCli
        dockerDesktop = [ordered]@{
            installed = [bool]$dockerDesktopPath
            path      = $dockerDesktopPath
        }
        wsl = [ordered]@{
            installed     = [bool]$wslCommand
            path          = if ($wslCommand) { $wslCommand.Source } else { $null }
            status        = $wslStatus
            distributions = $wslDistributions
        }
        xampp = Find-Xampp
        php = Get-CommandInfo -Name 'php' -VersionArguments @('--version')
        composer = Get-CommandInfo -Name 'composer' -VersionArguments @('--version')
        mysql = Get-CommandInfo -Name 'mysql' -VersionArguments @('--version')
    }
}

$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonReportPath -Encoding UTF8

$summary = @"
AI-Engineer Phase 0 System Audit
Generated: $($report.audit.generatedAt)
Project root: $($report.audit.projectRoot)

SYSTEM
Windows: $($report.system.windowsCaption)
Version/build: $($report.system.windowsVersion) / $($report.system.windowsBuild)
PowerShell: $($report.system.powershellVersion)
RAM: $($report.system.totalRamGB) GB total / $($report.system.availableRamGB) GB currently available

CPU
Name: $($report.cpu.name)
Cores/threads: $($report.cpu.physicalCores) / $($report.cpu.logicalProcessors)

GPU
$(
    ($report.gpu | ForEach-Object {
        "- $($_.name) | reported VRAM: $($_.adapterRamGB) GB | driver: $($_.driverVersion)"
    }) -join [Environment]::NewLine
)

PROJECT DRIVE
Drive: $($report.projectDrive.drive)
Exists: $($report.projectDrive.exists)
Filesystem: $($report.projectDrive.fileSystem)
Total: $($report.projectDrive.totalGB) GB
Free: $($report.projectDrive.freeGB) GB

TOOLS
VS Code: $($report.tools.vscode.installed) | $($report.tools.vscode.version)
Git: $($report.tools.git.installed) | $($report.tools.git.version)
Python: $($report.tools.python.installed) | $($report.tools.python.version)
Node.js: $($report.tools.node.installed) | $($report.tools.node.version)
npm: $($report.tools.npm.installed) | $($report.tools.npm.version)
Docker CLI: $($report.tools.dockerCli.installed) | $($report.tools.dockerCli.version)
Docker Desktop: $($report.tools.dockerDesktop.installed)
WSL: $($report.tools.wsl.installed)
XAMPP: $($report.tools.xampp.installed) | $($report.tools.xampp.path)
PHP: $($report.tools.php.installed) | $($report.tools.php.version)
Composer: $($report.tools.composer.installed) | $($report.tools.composer.version)
MySQL CLI: $($report.tools.mysql.installed) | $($report.tools.mysql.version)

REPORT FILES
JSON: $jsonReportPath
Text: $textReportPath
"@

$summary | Set-Content -LiteralPath $textReportPath -Encoding UTF8
Write-Host ''
Write-Host $summary
Write-Host ''
Write-Host 'Audit completed safely. No software or Windows setting was changed.' -ForegroundColor Green
