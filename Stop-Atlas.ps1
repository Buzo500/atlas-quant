$ErrorActionPreference = 'Stop'
$atlasPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $atlasPython)) { throw 'No hay una instalación de ATLAS en esta carpeta.' }
& $atlasPython (Join-Path $PSScriptRoot 'tools/run_atlas.py') --stop
exit $LASTEXITCODE
