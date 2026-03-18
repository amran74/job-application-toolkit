$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$BackupDir = Join-Path $Root "jobtracker_backup_$Timestamp"
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

Copy-Item (Join-Path $Root "jobtracker") -Destination (Join-Path $BackupDir "jobtracker") -Recurse -Force
Copy-Item (Join-Path $Root "jobs.db") -Destination (Join-Path $BackupDir "jobs_$Timestamp.db") -Force

$ZipPath = Join-Path $Root "jobtracker_backup_$Timestamp.zip"
Compress-Archive -Path (Join-Path $BackupDir "*") -DestinationPath $ZipPath -Force

Write-Host "Backup created:"
Write-Host "Folder: $BackupDir"
Write-Host "Zip:    $ZipPath"
