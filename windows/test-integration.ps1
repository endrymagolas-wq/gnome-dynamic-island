$ErrorActionPreference = 'Stop'
$ctl=Join-Path $PSScriptRoot 'control.ps1'
$evidence=Join-Path $PSScriptRoot 'verification'
$checks=[System.Collections.Generic.List[object]]::new()
function State { & $ctl -Command status | ConvertFrom-Json }
function Check([bool]$Condition,[string]$Name) { $checks.Add(@{name=$Name;passed=$Condition}); if (-not $Condition) { throw "FAIL: $Name" } }
function Wait-Water([bool]$Expected) {
    $deadline=[DateTime]::UtcNow.AddSeconds(12)
    do { $s=State; if ($s.wallpaperPreferences.Water -eq $Expected) { return $s }; Start-Sleep -Milliseconds 250 } while ([DateTime]::UtcNow -lt $deadline)
    throw 'Lively property was not persisted'
}
$initial=State
try {
    $different= -not $initial.wallpaperPreferences.Water
    $changed=& $ctl -Command wallpaper -Property water -Value ([int]$different) | ConvertFrom-Json
    Check $changed.ok 'Lively CLI accepts changing animated water'
    $readback=Wait-Water $different
    Check ($readback.wallpaperPreferences.Water -eq $different) 'Changed water property read back from Lively SaveData'
    $restored=& $ctl -Command wallpaper -Property water -Value ([int]$initial.wallpaperPreferences.Water) | ConvertFrom-Json
    Check $restored.ok 'Lively accepts restoring the previous water setting'
    $readback=Wait-Water $initial.wallpaperPreferences.Water
    Check ($readback.wallpaperPreferences.Water -eq $initial.wallpaperPreferences.Water -and $readback.wallpaperPreferences.Quality -eq $initial.wallpaperPreferences.Quality -and $readback.wallpaperPreferences.TimeOfDay -eq $initial.wallpaperPreferences.TimeOfDay) 'Water restored; quality and lighting preserved'
    if ($initial.focusSeconds -eq 0) {
        & $ctl -Command focus -Seconds 120 | Out-Null
        $before=State
        Check ($before.focusSeconds -gt 110 -and $before.focusSeconds -le 120) 'Focus timer starts with absolute deadline'
        & $ctl -Command quit | Out-Null
        & (Join-Path $PSScriptRoot 'start.ps1')
        Start-Sleep -Milliseconds 700
        $after=State
        Check ($after.focusSeconds -gt 100 -and $after.focusSeconds -lt $before.focusSeconds) 'Focus timer survives a real process restart without resetting'
        & $ctl -Command focus-stop | Out-Null
        Check ((State).focusSeconds -eq 0) 'Focus timer stops and clears the persisted deadline'
    }
    $pidBefore=(State).pid
    & (Join-Path $PSScriptRoot 'start.ps1')
    Start-Sleep -Milliseconds 700
    Check ((State).pid -eq $pidBefore) 'Second launcher invocation reuses the existing island'
} finally {
    & $ctl -Command wallpaper -Property water -Value ([int]$initial.wallpaperPreferences.Water) | Out-Null
    if ($initial.focusSeconds -eq 0) { & $ctl -Command focus-stop | Out-Null }
    $checks | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $evidence 'integration-checks.json')
}
Write-Output "PASS integration checks: $($checks.Count)"
