param([switch]$MeasurementsOnly,[switch]$TransitionOnly,[switch]$PauseOnly)
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
$evidence=Join-Path $root 'docs/evidence/resort/v6'
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
function Run-Python([string]$script,[string]$argument,[string]$log){
    $output=Join-Path $evidence $log
    $errors=$output+'.stderr'
    $process=Start-Process -FilePath (Get-Command python).Source -ArgumentList @($script,$argument) -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $output -RedirectStandardError $errors
    if(Test-Path $errors){Get-Content $errors | Add-Content $output;Remove-Item -LiteralPath $errors}
    if($process.ExitCode -ne 0){throw ('Python check failed (exit '+$process.ExitCode+'): '+$output)}
}
try {
    Restart-Core 1
    Restart-Host $false
    Select-Mode 'runtime'
    if(-not $MeasurementsOnly -and -not $TransitionOnly -and -not $PauseOnly){
        foreach($check in @('reactions','ambient','controls','lighting')){Run-Python 'tools/check_native_resort.py' $check ($check+'.log')}
    }
    if(-not $TransitionOnly -and -not $PauseOnly){foreach($format in @('video','atlas','still')){
        Select-Mode $format
        $label=if($format -eq 'still'){'still-v6'}else{$format+'-v6-720'}
        Run-Python 'tools/benchmark_resort.py' $label ($label+'.log')
    }
    Select-Mode 'runtime'
    python wallpaper/emit.py done;Check-Exit
    Run-Python 'tools/benchmark_resort.py' 'runtime-v6-coffee' 'coffee.log'
    python wallpaper/emit.py starting;Check-Exit
    python wallpaper/emit.py editing;Check-Exit
    Run-Python 'tools/benchmark_resort.py' 'runtime-v6-editing' 'editing.log'
    }
    if(-not $PauseOnly){
        Select-Mode 'runtime-transition'
        Run-Python 'tools/benchmark_resort.py' 'runtime-v6-transition' 'transition.log'
    }
    Select-Mode 'runtime'
    # Pause an initialized, advancing player. Coverage policy is restored only
    # afterwards, so a covered desktop cannot suspend initial page loading.
    $ready=$false
    for($attempt=0;$attempt -lt 30;$attempt++){
        $current=Invoke-RestMethod 'http://127.0.0.1:18765/bench-metrics'
        if($current.format -eq 'video' -and $current.videoWidth -eq 1920 -and $current.totalVideoFrames -gt 30 -and $null -eq $current.lighting.b -and $current.lighting.decoderCount -eq 1 -and -not $current.paused){$ready=$true;break}
        Start-Sleep -Seconds 1
    }
    if(-not $ready){throw 'Native player did not start before pause measurement'}
    try {
        Start-Process -FilePath $cli -ArgumentList 'app --play false' -WindowStyle Hidden -Wait
        Run-Python 'tools/benchmark_resort.py' 'runtime-v6-paused' 'paused.log'
    } finally {
        Start-Process -FilePath $cli -ArgumentList 'app --play true' -WindowStyle Hidden -Wait
    }
} finally {
    Restart-Core $saved
    Restart-Host $true
    $env:RESORT_NATIVE_EVIDENCE=$previousEvidence
    Select-Mode 'runtime'
}
$policy=Get-Content -LiteralPath $settings -Raw | ConvertFrom-Json
@{restoredFullscreenPause=$policy.AppFullscreenPause;observerEnabled=$true;pauseMeasurement='Lively native pause callback via CLI; desktop was not fully covered during this run'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'restored-pause-policy.json')
& (Join-Path $root 'wallpaper/launch.ps1')
Write-Host 'PASS requested native V6 checks; ordinary wallpaper, observer and pause policy restored'
