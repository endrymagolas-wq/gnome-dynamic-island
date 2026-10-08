param([string]$Evidence = (Join-Path $PSScriptRoot 'verification'))
$ErrorActionPreference='Stop'
$ctl=Join-Path $PSScriptRoot 'control.ps1'
$exe=Join-Path $PSScriptRoot 'app\IslandDesktop.exe'
$env:DOTNET_ROOT=Join-Path $PSScriptRoot 'runtime'
$data=Join-Path $env:LOCALAPPDATA 'IslandDesktopWindows'
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
$checks=[System.Collections.Generic.List[object]]::new()
function Check([bool]$Condition,[string]$Name) { $checks.Add(@{name=$Name;passed=$Condition});if(-not $Condition){throw "FAIL: $Name"} }
$initial=& $ctl -Command status | ConvertFrom-Json
if($initial.airplay.Connected){throw 'Stop active AirPlay playback before running the crash recovery test.'}
$owned=Get-CimInstance Win32_Process -Filter ("ProcessId="+$initial.pid)
if($owned.ExecutablePath -ne $exe){throw 'The running island does not belong to this exact package.'}
$launcher=Get-Process -Id $owned.ParentProcessId
$launcherInfo=Get-CimInstance Win32_Process -Filter ("ProcessId="+$owned.ParentProcessId)
if($launcherInfo.ExecutablePath -ne (Join-Path $PSScriptRoot 'IslandDesktop.exe')){throw 'The current package launcher must own the island.'}
try {
    & $ctl -Command inspect-ui | Out-Null
    $opened=& $ctl -Command nav -Id tray | ConvertFrom-Json
    Check ($opened.shell.nativeTray.open -and $opened.shell.nativeTray.taskbarTransparent) 'Crash fixture owns an open background tray and transparent taskbar lease'
    $layer=Get-Content -LiteralPath (Join-Path $data 'tray-layer-state.txt')
    Stop-Process -Id $owned.ProcessId -Force
    if(-not $launcher.WaitForExit(5000)){throw 'Portable launcher did not finish recovery.'}
    $probe=Join-Path $Evidence 'tray-after-crash.json'
    $process=Start-Process -FilePath $exe -ArgumentList @('--shell-probe',('"'+$probe+'"')) -PassThru -WindowStyle Hidden
    if(-not $process.WaitForExit(10000) -or $process.ExitCode -ne 0){throw 'Recovery probe failed.'}
    $restored=Get-Content -LiteralPath $probe -Raw | ConvertFrom-Json
    Check ($restored.style -eq [long]$layer[0] -and (([long]$layer[0] -band 0x80000) -eq 0 -or ($restored.alpha -eq [byte]$layer[2] -and $restored.flags -eq [uint]$layer[3] -and $restored.color -eq [uint]$layer[1]))) 'Portable launcher restores the actual original taskbar layer style after the island crashes'
    Check ($restored.visible -eq $initial.shell.originalTaskbarVisible -and $restored.state -eq $initial.shell.originalTaskbarState) 'Original taskbar visibility and autohide state return after the crash'
    Check (@('tray-layer-state.txt','taskbar-state.txt','taskbar-owner.txt','taskbar-visible.txt').Where({Test-Path -LiteralPath (Join-Path $data $_)}).Count -eq 0) 'Recovery clears only the owned taskbar lease files'
    Check ($null -eq (Get-Process -Id $initial.airplay.Pid -ErrorAction SilentlyContinue)) 'The crashed island does not leave its AirPlay receiver running'
} finally {
    & (Join-Path $PSScriptRoot 'start.ps1')
    $checks | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Evidence 'tray-crash-recovery.json') -Encoding utf8
}
[pscustomobject]@{passed=$checks.Count;failed=0;method='Force-terminate only this package-owned island process; read back Explorer state from a separate native probe'} | ConvertTo-Json
