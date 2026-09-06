$ErrorActionPreference = 'Stop'
$atlasRoot = $PSScriptRoot
$atlasPythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $atlasPythonCommand) { throw 'Instala Python 3.12 o posterior y añádelo al PATH.' }
$atlasPnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $atlasPnpmCommand) { throw 'Instala Node.js >=22.13 y pnpm; después vuelve a ejecutar este script.' }
Push-Location $atlasRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        & $atlasPythonCommand.Source -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno Python.' }
    }
    & '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias Python.' }
    & $atlasPnpmCommand.Source --dir frontend install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias de la interfaz.' }
    Write-Output 'Instalación completada. Ejecuta Start-Atlas.ps1 -OpenBrowser.'
} finally { Pop-Location }
