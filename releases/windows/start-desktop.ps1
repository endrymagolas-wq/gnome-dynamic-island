param([switch]$InstallHooks,[switch]$Diagnose)
. (Join-Path $PSScriptRoot 'Release-Common.ps1')
if($Diagnose){Get-ReleaseDiagnostics;exit 0}
$alreadyRunning=Test-ReleaseIslandOwner
$wall=Join-Path $ReleaseRoot 'wallpaper/server.py'
if(Test-Path -LiteralPath $wall){Start-ReleaseWallpaper -InstallHooks:$InstallHooks}
$exe=Join-Path $ReleaseRoot 'IslandDesktop.exe'
if(-not(Test-Path -LiteralPath $exe)){throw 'This package does not include IslandDesktop.exe.'}
if(-not $alreadyRunning){Start-Process -FilePath $exe -WorkingDirectory $ReleaseRoot -WindowStyle Hidden}
