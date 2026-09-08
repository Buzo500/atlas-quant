param([Parameter(Mandatory=$true)][string]$BackupPath)
$ErrorActionPreference = 'Stop'
$atlasPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $atlasPython)) { throw 'Primero ejecuta Install-Atlas.ps1.' }
& $atlasPython (Join-Path $PSScriptRoot 'tools/backup_atlas.py') --restore $BackupPath
exit $LASTEXITCODE
