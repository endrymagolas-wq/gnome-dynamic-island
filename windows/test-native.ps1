param([string]$Evidence = (Join-Path $PSScriptRoot 'verification'))
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
$exe = Join-Path $PSScriptRoot 'app\IslandDesktop.exe'
$env:DOTNET_ROOT = Join-Path $PSScriptRoot 'runtime'
$env:DOTNET_ROOT_X64 = $env:DOTNET_ROOT
$ctl = Join-Path $PSScriptRoot 'control.ps1'
$fixtureFile = Join-Path $Evidence 'fixture-state.json'
$fixture = $null
$checks = [System.Collections.Generic.List[object]]::new()
function Check([bool]$Condition,[string]$Name) {
    $checks.Add(@{name=$Name;passed=$Condition})
    if (-not $Condition) { throw "FAIL: $Name" }
}
function Control([string]$Command) { & $ctl -Command $Command | ConvertFrom-Json }
function Wait-State([scriptblock]$Condition,[int]$Seconds=12) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do { $state=Control status; if (& $Condition $state) { return $state }; Start-Sleep -Milliseconds 250 } while ([DateTime]::UtcNow -lt $deadline)
    throw 'Timed out waiting for native state'
}
function Wait-Fixture([scriptblock]$Condition) {
    $deadline = [DateTime]::UtcNow.AddSeconds(12)
    do { $fixtureState = Get-Content $fixtureFile -Raw | ConvertFrom-Json; if (& $Condition $fixtureState) { return $fixtureState }; Start-Sleep -Milliseconds 250 } while ([DateTime]::UtcNow -lt $deadline)
    throw 'Timed out waiting for independent fixture readback'
}
try {
    $initial=Wait-State {param($s) $s.audio.Available -and $s.wallpaper.Connected}
    $initial | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $Evidence 'initial.json')
    Check $initial.audio.Available 'Real Windows audio endpoint available'
    Check ($initial.playerLabel -eq 'Автоматичний вибір плеєра') 'Automatic player label is initialized on cold start without a media session'
    Check $initial.wallpaper.Connected 'Existing V6 wallpaper server connected'
    Check $initial.wallpaperPreferences.Ready 'V6 properties read from the current Lively installation'
    $sameVolume = & $ctl -Command volume -Value $initial.audio.Volume | ConvertFrom-Json
    Check $sameVolume.ok 'Core Audio accepts current master volume'
    $readback=Control status
    Check ([Math]::Abs($readback.audio.Volume-$initial.audio.Volume) -lt 0.005) 'Master volume read back without changing user volume'
    $fixture = Start-Process -FilePath $exe -ArgumentList @('--fixture',('"'+$fixtureFile+'"')) -WindowStyle Hidden -PassThru
    $state=Wait-State {param($s) $s.players.Count -gt 0 -and ($s.players | Where-Object {$_.Id -match 'Island|NativeFixture'})}
    $fixtureChoice = $state.players | Where-Object {$_.Id -match 'Island|NativeFixture'} | Select-Object -First 1
    & $ctl -Command select -Id $fixtureChoice.Id | Out-Null
    $state=Wait-State {param($s) $s.media.Title -eq 'Island Windows · test 1' -and $s.media.Playing}
    Check $state.media.CanToggle 'Fixture publishes native play/pause capability'
    Check $state.hasArtwork 'Album artwork read from the actual Windows media session'
    $fixtureAudio = $state.audio.Apps | Where-Object Pid -eq $fixture.Id | Select-Object -First 1
    Check ($null -ne $fixtureAudio) 'Fixture has a real per-process audio session'
    $appVolume = & $ctl -Command volume -Value 0.37 -PidValue $fixture.Id | ConvertFrom-Json
    Check $appVolume.ok 'Per-process volume accepted'
    $state=Wait-State {param($s) ($s.audio.Apps | Where-Object Pid -eq $fixture.Id | Select-Object -First 1).Volume -lt 0.38}
    Check ([Math]::Abs(($state.audio.Apps | Where-Object Pid -eq $fixture.Id | Select-Object -First 1).Volume-0.37) -lt 0.005) 'Per-process volume read back from Core Audio'
    & $ctl -Command volume -Value $fixtureAudio.Volume -PidValue $fixture.Id | Out-Null
    $appMute = & $ctl -Command mute -Boolean -PidValue $fixture.Id | ConvertFrom-Json
    Check $appMute.ok 'Per-process mute accepted'
    $state=Wait-State {param($s) ($s.audio.Apps | Where-Object Pid -eq $fixture.Id | Select-Object -First 1).Muted}
    Check (($state.audio.Apps | Where-Object Pid -eq $fixture.Id | Select-Object -First 1).Muted) 'Per-process mute read back from Core Audio'
    & $ctl -Command mute -PidValue $fixture.Id | Out-Null
    & $ctl -Command reactive -Boolean | Out-Null
    Check (Control status).reactiveEnabled 'WASAPI loopback capture starts'
    & $ctl -Command reactive | Out-Null
    Check (-not (Control status).reactiveEnabled) 'WASAPI loopback capture stops'
    $pause=Control pause; Check $pause.ok 'Pause accepted through Windows media API'
    $state=Wait-State {param($s) -not $s.media.Playing}
    $fixtureState=Wait-Fixture {param($f) $f.state -eq 'Paused'}
    Check ($fixtureState.state -eq 'Paused') 'Independent fixture confirms actual pause'
    $play=Control play; Check $play.ok 'Play accepted through Windows media API'
    $state=Wait-State {param($s) $s.media.Playing}
    $fixtureState=Wait-Fixture {param($f) $f.state -eq 'Playing'}
    Check ($fixtureState.state -eq 'Playing') 'Independent fixture confirms actual play'
    $next=Control next; Check $next.ok 'Next accepted'
    $state=Wait-State {param($s) $s.media.Title -eq 'Island Windows · test 2'}
    $fixtureState=Wait-Fixture {param($f) $f.track -eq 2}
    Check ($fixtureState.track -eq 2) 'Independent fixture confirms next track'
    $previous=Control previous; Check $previous.ok 'Previous accepted'
    $state=Wait-State {param($s) $s.media.Title -eq 'Island Windows · test 1'}
    $fixtureState=Wait-Fixture {param($f) $f.track -eq 1}
    Check ($fixtureState.track -eq 1) 'Independent fixture confirms previous track'
    $seek=& $ctl -Command seek -Position 45 | ConvertFrom-Json
    Check $seek.ok 'Seek accepted'
    $state=Wait-State {param($s) $s.media.Position -ge 44 -and $s.media.Position -lt 55}
    $fixtureState=Wait-Fixture {param($f) $f.position -ge 44}
    Check ($fixtureState.position -ge 44) 'Independent fixture confirms seek'
    $state | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $Evidence 'native-media.json')
    & $ctl -Command expand | Out-Null
    Start-Sleep -Milliseconds 800
    $expanded=Control status
    Check ($expanded.expanded -and [Math]::Abs($expanded.width-380) -lt 1) 'Native island expands to Linux-derived panel width'
    & $ctl -Command snapshot -Path (Join-Path $Evidence 'media-panel.png') | Out-Null
    & $ctl -Command desktop | Out-Null
    Start-Sleep -Milliseconds 800
    & $ctl -Command snapshot -Path (Join-Path $Evidence 'desktop-panel.png') | Out-Null
    & $ctl -Command settings | Out-Null
    Start-Sleep -Milliseconds 300
    & $ctl -Command snapshot -Path (Join-Path $Evidence 'settings-panel.png') | Out-Null
    & $ctl -Command collapse | Out-Null
    Start-Sleep -Milliseconds 500
    $compact=Control status
    Check (-not $compact.expanded -and [Math]::Abs($compact.width-128) -lt 1 -and [Math]::Abs($compact.height-26) -lt 1) 'Native island returns to compact pill'
    & $ctl -Command snapshot -Path (Join-Path $Evidence 'compact.png') | Out-Null
    Stop-Process -Id $fixture.Id
    $fixture=$null
    $state=Wait-State {param($s) -not ($s.players | Where-Object {$_.Id -eq $fixtureChoice.Id})}
    Check ($state.media.Source -ne $fixtureChoice.Id) 'Removed player is discarded; automatic selection recovers'
} finally {
    if ($fixture -and -not $fixture.HasExited) { Stop-Process -Id $fixture.Id }
    try { & $ctl -Command select -Id '' | Out-Null; & $ctl -Command collapse | Out-Null } catch { }
    $checks | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $Evidence 'native-checks.json')
}
Write-Output "PASS native checks: $($checks.Count)"
