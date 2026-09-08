param([switch]$OpenBrowser)
$ErrorActionPreference = 'Stop'
$atlasRoot = $PSScriptRoot
$atlasPython = Join-Path $atlasRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $atlasPython)) { throw 'Primero ejecuta Install-Atlas.ps1.' }
$atlasRunner = Join-Path $atlasRoot 'tools/run_atlas.py'
$atlasArgs = @('-u', $atlasRunner, '--background')
if ($OpenBrowser) { $atlasArgs += '--open' }
& $atlasPython @atlasArgs
exit $LASTEXITCODE
