# Source-checkout launcher. Released ZIPs receive the reviewed portable launcher
# from releases/windows/start-desktop.ps1 instead.
param([switch]$InstallHooks)
$ErrorActionPreference='Stop'
$here=[IO.Path]::GetFullPath($PSScriptRoot)
$project=Split-Path $here -Parent
$wallpaper=Join-Path $project 'wallpaper/launch.ps1'
if(Test-Path -LiteralPath $wallpaper){& $wallpaper -InstallHooks:$InstallHooks}
$island=Join-Path $here 'IslandDesktop.exe'
if(-not(Test-Path -LiteralPath $island)){throw 'Build windows/build.ps1 first, or download the portable Windows release.'}
if(-not(Get-Process IslandDesktop -ErrorAction SilentlyContinue)){Start-Process -FilePath $island -WorkingDirectory $here -WindowStyle Hidden}
