param([ValidateSet('video','atlas','still','runtime','runtime-transition')][string]$Format='video')
$ErrorActionPreference='Stop'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'wallpaper/find-lively.ps1')
$app=Find-ResortLively
if(-not $app){throw 'A verified Lively Store installation is required.'}
$actual=Join-Path $env:LOCALAPPDATA ('Packages/'+$app.PackageFamilyName+'/LocalCache/Local/Lively Wallpaper/Library/wallpapers/resort-benchmark-'+$Format)
$alias=Join-Path $env:LOCALAPPDATA ('Lively Wallpaper/Library/wallpapers/resort-benchmark-'+$Format)
New-Item -ItemType Directory -Force -Path $actual | Out-Null
$info=Get-Content -LiteralPath (Join-Path (Split-Path $PSScriptRoot -Parent) 'wallpaper/LivelyInfo.json') -Raw | ConvertFrom-Json
$info.Title='Resort benchmark '+$Format
$info | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $actual 'LivelyInfo.json') -Encoding UTF8
if($Format.StartsWith('runtime')){
    $defaults=Join-Path (Split-Path $PSScriptRoot -Parent) 'wallpaper/LivelyProperties.json'
    Copy-Item -LiteralPath $defaults -Destination $actual
    # Measurement entries have controlled defaults; ordinary wallpaper settings
    # are migrated independently by launch.ps1 and are never reset here.
    $saved=Join-Path $env:LOCALAPPDATA ('Packages/'+$app.PackageFamilyName+'/LocalCache/Local/Lively Wallpaper/Library/SaveData/wpdata/resort-benchmark-'+$Format)
    if(Test-Path -LiteralPath $saved){
        foreach($monitor in Get-ChildItem -LiteralPath $saved -Directory){
            Copy-Item -LiteralPath $defaults -Destination (Join-Path $monitor.FullName 'LivelyProperties.json')
        }
    }
}
$page=if($Format -eq 'runtime-transition'){'index.html?preview=1&metrics=1&lightingMinute=541'}elseif($Format -eq 'runtime'){'index.html?metrics=1'}else{'benchmark.html?format='+$Format}
('<!doctype html><meta http-equiv="refresh" content="0;url=http://127.0.0.1:18765/wallpaper/'+$page+'">') | Set-Content -LiteralPath (Join-Path $actual 'bootstrap.html') -Encoding UTF8
$cli=Join-Path $env:LOCALAPPDATA 'ResortIsland/lively-cli/Livelycu.exe'
Start-Process -FilePath $cli -ArgumentList ('setwp --file "'+$alias+'"') -WindowStyle Hidden -Wait
