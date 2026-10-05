# Temporarily keep our desktop player active for measurements, then restore pause.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location $root
. (Join-Path $root 'wallpaper/find-lively.ps1')
$app=Find-ResortLively
if(-not $app){throw 'Verified Lively installation missing'}
$cache=Join-Path $env:LOCALAPPDATA ('Packages/'+$app.PackageFamilyName+'/LocalCache/Local/Lively Wallpaper')
$settings=Join-Path $cache 'Settings.json'
$layout=@(Get-Content -LiteralPath (Join-Path $cache 'WallpaperLayout.json') -Raw | ConvertFrom-Json)
if($layout.Count -ne 1 -or $layout[0].LivelyInfoPath -notlike '*\resort-*'){throw 'Another wallpaper owner is active; leave it untouched'}
if(Get-Process blender -ErrorAction SilentlyContinue){throw 'Stop owned render workers before measuring'}
$exe=Join-Path $app.InstallLocation 'Build/Lively.exe'
$cli=Join-Path $env:LOCALAPPDATA 'ResortIsland/lively-cli/Livelycu.exe'
$saved=(Get-Content -LiteralPath $settings -Raw | ConvertFrom-Json).AppFullscreenPause
$evidence=Join-Path $root 'docs/evidence/resort/v4'
New-Item -ItemType Directory -Force -Path $evidence | Out-Null
$previousEvidence=$env:RESORT_NATIVE_EVIDENCE
$env:RESORT_NATIVE_EVIDENCE=$evidence
function Restart-Core([int]$policy){
    $players=@(Get-Process Lively.Player.WebView2 -ErrorAction SilentlyContinue)
    if($players.Count -gt 1){throw 'More than one player; do not disturb other owners'}
    Get-Process Lively.Watchdog -ErrorAction SilentlyContinue | Stop-Process
    Get-Process Lively.Player.WebView2,Lively -ErrorAction SilentlyContinue | Stop-Process
    Start-Sleep -Seconds 2
    $data=Get-Content -LiteralPath $settings -Raw | ConvertFrom-Json
    $data.AppFullscreenPause=$policy
    $data | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $settings -Encoding UTF8
    Start-Process -FilePath $exe -ArgumentList 'app --showApp false' -WindowStyle Hidden
    Start-Sleep -Seconds 5
}
function Restart-Host([bool]$observe){
    $hostListener=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 18765 -State Listen -ErrorAction SilentlyContinue)
    foreach($listener in $hostListener){
        $proc=Get-CimInstance Win32_Process -Filter ('ProcessId='+$listener.OwningProcess)
        if($proc.CommandLine -notlike '*wallpaper*server.py*'){throw 'Port belongs to another server'}
        Stop-Process -Id $listener.OwningProcess
    }
    $arguments='"'+(Join-Path $root 'wallpaper/server.py')+'"'
    if(-not $observe){$arguments+=' --no-observer'}
    Start-Process -FilePath (Get-Command python).Source -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden
    Start-Sleep -Seconds 2
}
function Select-Mode([string]$format){
    Start-Process -FilePath $cli -ArgumentList 'closewp --monitor 1' -WindowStyle Hidden -Wait
    & (Join-Path $PSScriptRoot 'start_resort_benchmark.ps1') -Format $format
    Start-Sleep -Seconds 3
}
function Check-Exit {if($LASTEXITCODE -ne 0){throw 'Native check failed; see evidence logs'}}
try {
    Restart-Core 1
    Restart-Host $false
    Select-Mode 'runtime'
    python tools/check_native_resort.py reactions *> (Join-Path $evidence 'reactions.log');Check-Exit
    python tools/check_native_resort.py controls *> (Join-Path $evidence 'controls.log');Check-Exit
    foreach($format in @('video','atlas','still')){
        Select-Mode $format
        $label=if($format -eq 'still'){'still-v4'}else{$format+'-v4-720'}
        python tools/benchmark_resort.py $label *> (Join-Path $evidence ($label+'.log'));Check-Exit
    }
    Select-Mode 'runtime'
    python wallpaper/emit.py done;Check-Exit
    python tools/benchmark_resort.py runtime-v4-coffee *> (Join-Path $evidence 'coffee.log');Check-Exit
    python wallpaper/emit.py starting;Check-Exit
    python wallpaper/emit.py editing;Check-Exit
    python tools/benchmark_resort.py runtime-v4-editing *> (Join-Path $evidence 'editing.log');Check-Exit
} finally {
    Restart-Core $saved
    Restart-Host $true
    $env:RESORT_NATIVE_EVIDENCE=$previousEvidence
    Select-Mode 'runtime'
}
try {
    Start-Process -FilePath $cli -ArgumentList 'app --play false' -WindowStyle Hidden -Wait
    python tools/benchmark_resort.py runtime-v4-paused *> (Join-Path $evidence 'paused.log');Check-Exit
} finally {
    Start-Process -FilePath $cli -ArgumentList 'app --play true' -WindowStyle Hidden -Wait
}
$policy=Get-Content -LiteralPath $settings -Raw | ConvertFrom-Json
@{restoredFullscreenPause=$policy.AppFullscreenPause;observerEnabled=$true;pauseMeasurement='Lively native pause callback via CLI; desktop was not fully covered during this run'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'restored-pause-policy.json')
& (Join-Path $root 'wallpaper/launch.ps1')
Write-Host 'PASS native V4 reactions, controls, format comparison, native pause callback and restored policy'
