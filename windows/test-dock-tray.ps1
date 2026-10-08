param([string]$Evidence = (Join-Path $PSScriptRoot 'verification'))
$ErrorActionPreference='Stop'
$ctl=Join-Path $PSScriptRoot 'control.ps1'
$exe=Join-Path $PSScriptRoot 'app\IslandDesktop.exe'
$env:DOTNET_ROOT=Join-Path $PSScriptRoot 'runtime'
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
$checks=[System.Collections.Generic.List[object]]::new()
function Check([bool]$Condition,[string]$Name) { $checks.Add(@{name=$Name;passed=$Condition});if(-not $Condition){throw "FAIL: $Name"} }
function Probe([string]$Name) {
    $path=Join-Path $Evidence ($Name+'.json')
    $process=Start-Process -FilePath $exe -ArgumentList @('--shell-probe',('"'+$path+'"')) -PassThru -WindowStyle Hidden
    if(-not $process.WaitForExit(10000) -or $process.ExitCode -ne 0){throw 'Shell probe failed'}
    Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
}
try {
    & $ctl -Command inspect-ui | Out-Null
    $before=Probe 'tray-before'
    foreach($cycle in 1..3) {
        $opened=& $ctl -Command nav -Id tray | ConvertFrom-Json
        Check ($opened.shell.nativeTray.open -and $opened.shell.nativeTray.taskbarTransparent) "Cycle $cycle opens real icons while the Windows taskbar stays transparent"
        Check ($opened.shell.nativeTray.rectangle.top -lt 100 -and $opened.shell.nativeTray.rectangle.width -gt 80) "Cycle $cycle anchors the icon grid below the top panel"
        $closed=& $ctl -Command nav -Id tray | ConvertFrom-Json
        Check (-not $closed.shell.nativeTray.open -and -not $closed.shell.nativeTray.taskbarTransparent) "Cycle $cycle closes the icon grid"
        Start-Sleep -Milliseconds 100
        $after=Probe ('tray-after-'+$cycle)
        Check ($before.style -eq $after.style -and $before.attributes -eq $after.attributes -and (-not $before.attributes -or ($before.alpha -eq $after.alpha -and $before.color -eq $after.color -and $before.flags -eq $after.flags)) -and -not $after.visible -and $before.state -eq $after.state) "Cycle $cycle restores the actual taskbar style and autohide state"
    }
    $state=& $ctl -Command status | ConvertFrom-Json
    Check ($state.airplay.Enabled -and $state.airplay.Ready) 'The integrated AirPlay receiver stays ready after tray navigation'
} finally {
    & $ctl -Command inspect-off | Out-Null
    $checks | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Evidence 'dock-tray-lifecycle.json') -Encoding utf8
}
[pscustomobject]@{passed=$checks.Count;failed=0;method='Live application navigation and independent Win32 taskbar style probes'} | ConvertTo-Json
