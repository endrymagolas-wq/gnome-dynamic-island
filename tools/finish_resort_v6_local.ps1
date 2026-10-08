param([int]$OwnedBridgePid=0)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location $root
$stage=Join-Path $root 'wallpaper/assets/v6-stage'
$status=Join-Path $stage 'finish-progress.json'
function Status([string]$step){@{stage=$step;updatedAt=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $status}
function Check-Exit {if($LASTEXITCODE -ne 0){throw 'V6 verification failed; inspect finish-worker.log'}}
try {
    Status 'waiting-for-four-renders'
    while($true){
        $batch=Get-Content -LiteralPath (Join-Path $stage 'batch-progress.json') -Raw | ConvertFrom-Json
        if($batch.stage -eq 'complete'){break}
        $worker=Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*render_resort_v6_batch.py*' -and $_.Name -like 'python*'}
        if(-not $worker){throw 'Render batch stopped before completing all four phases'}
        Start-Sleep -Seconds 15
    }
    Status 'packaging-and-checking-seams'
    python tools/package_resort_v6.py;Check-Exit
    $env:RESORT_TEST_ASSETS=$stage
    node tests/resort-scene.mjs;Check-Exit
    node tests/resort-navigation.mjs;Check-Exit
    node tests/resort-lighting.mjs;Check-Exit
    node tests/resort-lighting-runtime.mjs;Check-Exit
    python tests/check_resort_depth.py;Check-Exit
    python tests/check_resort_construction_depth.py;Check-Exit
    $env:RESORT_TEST_ASSETS=$null
    Status 'promoting-complete-bundle'
    python tools/package_resort_v6.py --promote;Check-Exit
    if($OwnedBridgePid){
        $bridge=Get-CimInstance Win32_Process -Filter ('ProcessId='+$OwnedBridgePid)
        if($bridge){
            if($bridge.Name -ne 'blender.exe' -or $bridge.CommandLine -notlike '*blender-bootstrap.py*' -or $bridge.CommandLine -notlike ('*'+$root+'*')){throw 'Bridge PID ownership no longer matches'}
            Stop-Process -Id $OwnedBridgePid
        }
    }
    if(Get-Process blender -ErrorAction SilentlyContinue){throw 'A Blender process remains; postpone measurements without stopping another owner'}
    Status 'preparing-fair-atlas-comparison'
    python tools/prepare_resort_atlas.py;Check-Exit
    Status 'native-reactions-controls-and-performance'
    & tools/run_resort_v6_native.ps1
    Status 'verifying-final-evidence'
    python tools/report_resort_v6.py;Check-Exit
    python tools/validate_resort_v6.py;Check-Exit
    Status 'complete-awaiting-visual-review-and-pr-update'
} catch {
    @{stage='failed';error=$_.Exception.Message;updatedAt=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $status
    throw
}
