param([switch]$OpenBrowser)
$ErrorActionPreference = 'Stop'
$atlasRoot = $PSScriptRoot
$atlasPython = Join-Path $atlasRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $atlasPython)) { throw 'Primero ejecuta Install-Atlas.ps1.' }
$atlasLogDir = Join-Path $atlasRoot 'var/logs'
New-Item -ItemType Directory -Path $atlasLogDir -Force | Out-Null
$atlasRunner = Join-Path $atlasRoot 'tools/run_atlas.py'
$atlasArgs = @('-u', ('"' + $atlasRunner + '"'))
if ($OpenBrowser) { $atlasArgs += '--open' }
Start-Process -FilePath $atlasPython -ArgumentList $atlasArgs -WorkingDirectory $atlasRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $atlasLogDir 'launcher.log') -RedirectStandardError (Join-Path $atlasLogDir 'launcher-error.log')
Write-Output 'ATLAS está arrancando en http://127.0.0.1:3000. Registros: var/logs.'
