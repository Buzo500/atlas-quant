$ErrorActionPreference = 'Stop'
$atlasStop = Join-Path $PSScriptRoot 'var/atlas.stop'
New-Item -ItemType Directory -Path (Split-Path -Parent $atlasStop) -Force | Out-Null
Set-Content -LiteralPath $atlasStop -Value 'stop' -Encoding ascii
Write-Output 'Se ha solicitado detener el motor y la interfaz de ATLAS.'
