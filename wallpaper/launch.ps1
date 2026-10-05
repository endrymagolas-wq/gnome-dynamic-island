param([switch]$InstallHooks)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonExe = (Get-Command python).Source
$islandState = Join-Path $env:LOCALAPPDATA 'ResortIsland'
New-Item -ItemType Directory -Force -Path $islandState | Out-Null
if (-not (Test-NetConnection 127.0.0.1 -Port 18765 -InformationLevel Quiet -WarningAction SilentlyContinue)) {
    Start-Process -FilePath $pythonExe -ArgumentList ('"' + (Join-Path $PSScriptRoot 'server.py') + '"') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $islandState 'server.log') -RedirectStandardError (Join-Path $islandState 'server-error.log')
}
if ($InstallHooks) { & $pythonExe (Join-Path $projectRoot 'assistant/claude_hook.py') --install }
$livelyApp = Get-AppxPackage '*LivelyWallpaper*' | Select-Object -First 1
if (-not $livelyApp) { throw 'Install Lively Wallpaper from its official Microsoft Store page first.' }
$livelyExe = Join-Path $livelyApp.InstallLocation 'Build/Lively.exe'
$livelyCli = Join-Path $islandState 'lively-cli/Livelycu.exe'
if (-not (Test-Path -LiteralPath $livelyCli)) {
    $cliArchive = Join-Path $islandState 'lively_command_utility.zip'
    Invoke-WebRequest 'https://github.com/lively-community/lively/releases/download/v2.0.4.0/lively_command_utility.zip' -OutFile $cliArchive
    Expand-Archive -LiteralPath $cliArchive -DestinationPath (Join-Path $islandState 'lively-cli') -Force
}
$livelyLibrary = Join-Path $env:LOCALAPPDATA 'Lively Wallpaper/Library/wallpapers/resort-island-blender'
$actualLibrary = Join-Path $env:LOCALAPPDATA ('Packages/' + $livelyApp.PackageFamilyName + '/LocalCache/Local/Lively Wallpaper/Library/wallpapers/resort-island-blender')
New-Item -ItemType Directory -Force -Path $actualLibrary | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'LivelyInfo.json'),(Join-Path $PSScriptRoot 'bootstrap.html') -Destination $actualLibrary
# Keep the user's saved water/quality choices on subsequent launches.
if(-not (Test-Path -LiteralPath (Join-Path $actualLibrary 'LivelyProperties.json'))){
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'LivelyProperties.json') -Destination $actualLibrary
}
$layout = Join-Path $env:LOCALAPPDATA ('Packages/' + $livelyApp.PackageFamilyName + '/LocalCache/Local/Lively Wallpaper/WallpaperLayout.json')
if ((Test-Path -LiteralPath $layout) -and -not (Test-Path -LiteralPath (Join-Path $islandState 'previous-layout.json'))) { Copy-Item -LiteralPath $layout -Destination (Join-Path $islandState 'previous-layout.json') }
Start-Process -FilePath $livelyExe -ArgumentList 'app','--showApp','false' -WindowStyle Hidden
Start-Sleep -Seconds 2
# Reload our existing entry when installing updated assets and scripts.
if(Test-Path -LiteralPath $layout){
    $existingLayout=Get-Content -LiteralPath $layout -Raw | ConvertFrom-Json
    if($existingLayout | Where-Object {$_.LivelyInfoPath -eq $livelyLibrary}){
        Start-Process -FilePath $livelyCli -ArgumentList 'closewp --monitor 1' -WindowStyle Hidden -Wait
    }
}
# Store package path translation is documented by Lively's CLI.
Start-Process -FilePath $livelyCli -ArgumentList ('setwp --file "' + $livelyLibrary + '"') -WindowStyle Hidden -Wait
Start-Sleep -Seconds 2
$liveLayout = Get-Content -LiteralPath $layout -Raw | ConvertFrom-Json
if (-not ($liveLayout | Where-Object { $_.LivelyInfoPath -eq $livelyLibrary })) { throw 'Lively has not confirmed Resort Island in its wallpaper layout.' }
Write-Host 'Resort Island confirmed in Lively. Disable it from Lively to restore your ordinary wallpaper.'
