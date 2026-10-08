$ErrorActionPreference = 'Stop'
$exe = Join-Path $PSScriptRoot 'IslandDesktop.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Build or unpack app/IslandDesktop.exe first.' }
Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden
