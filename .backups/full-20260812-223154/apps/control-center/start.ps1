#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = "F:\AI-Engineer\apps\control-center"

Set-Location $root

& npm.cmd run dev