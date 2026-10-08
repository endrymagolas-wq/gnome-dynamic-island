param([string]$Evidence = (Join-Path $PSScriptRoot 'verification'))
$ErrorActionPreference='Stop'
$ctl=Join-Path $PSScriptRoot 'control.ps1'
$checks=[System.Collections.Generic.List[object]]::new()
function Check([bool]$Condition,[string]$Name) {
    $checks.Add(@{name=$Name;passed=$Condition})
    if(-not $Condition){throw "FAIL: $Name"}
}
try {
    & $ctl -Command inspect-ui | Out-Null
    & $ctl -Command collapse | Out-Null
    & $ctl -Command panel | Out-Null
    Start-Sleep -Milliseconds 600
    $geometry=& $ctl -Command nav-geometry | ConvertFrom-Json
    foreach($button in $geometry){Check $button.hit ("Visible button receives pointer hits: "+$button.id)}
    foreach($id in @('apps','search')) {
        $state=& $ctl -Command nav -Id $id | ConvertFrom-Json
        Check ($state.shell.popup -eq $id) ("Navigation opens a real WPF popup: "+$id)
    }
    $state=& $ctl -Command nav -Id tray | ConvertFrom-Json
    Check ($state.shell.popup -eq 'tray' -and $state.shell.nativeTray.open) 'Navigation opens Explorer notification overflow with real background icons'
    Check $state.shell.nativeTray.taskbarTransparent 'Opening background icons keeps the Windows taskbar transparent'
    Check ($state.shell.nativeTray.rectangle.top -lt 100 -and $state.shell.nativeTray.rectangle.width -gt 80 -and $state.shell.nativeTray.rectangle.height -gt 40) 'The native background icons appear below the top panel'
    foreach($id in @('calendar','language','network')) {
        $state=& $ctl -Command nav -Id $id | ConvertFrom-Json
        Check ($state.shell.popup -eq $id) ("Navigation opens a real WPF popup: "+$id)
    }
    Check (-not $state.shell.nativeTray.open -and -not $state.shell.nativeTray.taskbarTransparent) 'Another navigation button closes the background icons and restores Explorer'
    $state=& $ctl -Command nav -Id volume | ConvertFrom-Json
    Check ($state.expanded -and $null -eq $state.shell.popup) 'Media navigation closes the prior popup and opens the island'
    $state=& $ctl -Command nav -Id settings | ConvertFrom-Json
    Check $state.expanded 'Settings navigation opens the system view'
    Check (-not ($state.shell.dockApps -contains 'ChatGPT Classic')) 'Classic ChatGPT is excluded from the live dock'
    $expected=@('Файли','Google Chrome','YouTube Music','Netflix','Crunchyroll','MiniMax Code','Visual Studio Code','Codex','Antigravity','Claude','Docker Desktop')
    Check (($state.shell.dockPins -join '|') -eq ($expected -join '|')) 'All eleven requested apps stay pinned in screenshot order'
    Check (@($state.shell.dockEntries | Where-Object { $_.pinned -and -not $_.hasIcon }).Count -eq 0) 'Every requested pin uses its installed app icon'
    foreach($name in @('Файли','Codex','Claude','Docker Desktop')) { Check (@($state.shell.dockApps | Where-Object { $_ -eq $name }).Count -eq 1) ("Pinned and running app is not duplicated: "+$name) }
    $checks | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Evidence 'navigation-regression.json') -Encoding utf8
    [pscustomobject]@{passed=$checks.Count;failed=0;method='Native WPF input hit testing and click handlers; real pointer evidence is recorded separately'} | ConvertTo-Json
} finally {
    & $ctl -Command collapse | Out-Null
    & $ctl -Command inspect-off | Out-Null
}
