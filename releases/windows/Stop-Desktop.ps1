param([switch]$Diagnose)
. (Join-Path $PSScriptRoot 'Release-Common.ps1')
if($Diagnose){Get-ReleaseDiagnostics;exit 0}
$ours=@(Get-Process IslandDesktop -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq (Join-Path $ReleaseRoot 'app/IslandDesktop.exe')})
if($ours.Count){& (Join-Path $ReleaseRoot 'control.ps1') -Command quit | Out-Null}
if(Test-Path -LiteralPath (Join-Path $ReleaseRoot 'wallpaper/server.py')){Restore-ReleaseWallpaper}
Write-Host 'This package is stopped. Island Desktop restores the native taskbar when it exits.'
