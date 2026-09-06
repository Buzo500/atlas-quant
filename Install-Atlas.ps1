$ErrorActionPreference = 'Stop'
$atlasPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $atlasPython)) {
    $atlasCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $atlasCommand) { throw 'Instala Python 3.12 o posterior y añádelo al PATH.' }
    $atlasPython = $atlasCommand.Source
}
& $atlasPython (Join-Path $PSScriptRoot 'tools/install_atlas.py')
exit $LASTEXITCODE
