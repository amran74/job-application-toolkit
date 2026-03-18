$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
& (Join-Path $Root "backup_jobtracker.ps1")
& (Join-Path $Root "run_jobtracker.ps1")
