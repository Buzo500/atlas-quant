$ErrorActionPreference = 'Stop'
$atlasPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $atlasPython)) { throw 'Primero ejecuta Install-Atlas.ps1.' }
& $atlasPython (Join-Path $PSScriptRoot 'tools/run_atlas.py') --status
exit $LASTEXITCODE
