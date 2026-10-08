param([switch]$Diagnose)
. (Join-Path $PSScriptRoot 'Release-Common.ps1')
if($Diagnose){Get-ReleaseDiagnostics;exit 0}
Restore-ReleaseWallpaper
