param([Parameter(Mandatory=$true)][string]$Package,[Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
$oldLocal=$env:LOCALAPPDATA;$temp=Join-Path ([IO.Path]::GetTempPath()) ('island-launcher-test-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $temp | Out-Null
$count=0;$child=$null
function Check([bool]$Result,[string]$Name){if(-not $Result){throw ('Failed: '+$Name)};$script:count++}
try {
    $env:LOCALAPPDATA=$temp
    . (Join-Path ([IO.Path]::GetFullPath($Package)) 'Release-Common.ps1')
    $state=Get-ReleaseState
    Check ($state.StartsWith($temp)) 'State is inside the isolated LOCALAPPDATA'
    $child=Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList '-NoProfile -Command "Start-Sleep -Seconds 30"' -WindowStyle Hidden -PassThru
    $record=@{pid=$child.Id;started=$child.StartTime.ToUniversalTime().ToString('o')}
    Check (Test-OwnedProcess $record $child.Path $null) 'Exact process path and creation time accepted'
    Check (-not(Test-OwnedProcess $record (Join-Path $temp 'other.exe') $null)) 'Different executable rejected'
    Check (-not(Test-OwnedProcess $record $child.Path 'server-that-was-not-started.py')) 'Different command script rejected'
    $record.started='2000-01-01T00:00:00.0000000Z'
    Check (-not(Test-OwnedProcess $record $child.Path $null)) 'Reused PID creation time rejected'
    $record.started=$child.StartTime.ToUniversalTime().ToString('o')
    Write-ReleaseJson (Join-Path $state 'host-owner.json') $record
    Stop-ReleaseHost
    $child.Refresh();Check (-not $child.HasExited) 'Stop refuses unrelated process even with local ownership file'
    Check (-not(Test-Path -LiteralPath (Join-Path $state 'host-owner.json'))) 'Stale ownership removed safely'
    function Test-LoopbackPort([int]$Port){return $true}
    function Get-ReleaseHostIdentity{return [pscustomobject]@{packageId='foreign-package'}}
    $rejected=$false;try{Start-ReleaseHost}catch{$rejected=$_.Exception.Message.Contains('Another wallpaper host')}
    Check $rejected 'Foreign loopback host is refused'
    function Get-ReleaseHostIdentity{return [pscustomobject]@{packageId=$ReleaseInfo.packageId}}
    Start-ReleaseHost
    Check (-not(Test-Path -LiteralPath (Join-Path $state 'host-owner.json'))) 'Matching host reused without taking ownership'
    $layout=Join-Path $temp 'layout.json';$owner=Join-Path $state 'wallpaper-owner.json';$backup=Join-Path $state 'previous-lively-layout.json'
    $screen=[pscustomobject]@{Index=1;DeviceId='synthetic-test-display'}
    Write-ReleaseJson $layout @(@{LivelyScreen=$screen;LivelyInfoPath='synthetic-new-wallpaper'})
    Write-ReleaseJson $owner @{layout=$layout;entry='synthetic-new-wallpaper'}
    Write-ReleaseJson $backup @(@{LivelyScreen=$screen;LivelyInfoPath='synthetic-previous-wallpaper'})
    $script:commands=New-Object 'System.Collections.Generic.List[string]';$script:hostStops=0
    function Invoke-ReleaseLively([string]$Arguments){$script:commands.Add($Arguments)}
    function Stop-ReleaseHost{$script:hostStops++}
    Restore-ReleaseWallpaper
    Check ($commands.Count -eq 2) 'Restore issues only close and previous-entry activation'
    Check ($commands[0] -eq 'closewp --monitor 1') 'Restore closes the owned screen only'
    Check ($commands[1] -eq 'setwp --file "synthetic-previous-wallpaper" --monitor 1') 'Restore selects that screen previous entry'
    Check ($hostStops -eq 1) 'Restore stops owned host through ownership helper'
    Check (-not(Test-Path -LiteralPath $owner)) 'Restore removes wallpaper ownership'
    Check (-not(Test-Path -LiteralPath $backup)) 'Restore removes consumed layout snapshot'
    Write-ReleaseJson $layout @(@{LivelyScreen=$screen;LivelyInfoPath='synthetic-later-user-choice'})
    Write-ReleaseJson $owner @{layout=$layout;entry='synthetic-new-wallpaper'}
    Write-ReleaseJson $backup @(@{LivelyScreen=$screen;LivelyInfoPath='synthetic-previous-wallpaper'})
    $commands.Clear();Restore-ReleaseWallpaper
    Check ($commands.Count -eq 0) 'Later user wallpaper choice is preserved'
    # Compile the actual native console Job owner without starting any receiver.
    $airplay=Get-Content -LiteralPath (Join-Path ([IO.Path]::GetFullPath($Package)) 'Start-AirPlay.ps1') -Raw -ErrorAction SilentlyContinue
    if(-not $airplay){$airplay=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Start-AirPlay.ps1') -Raw}
    $match=[regex]::Match($airplay,"(?s)Add-Type -TypeDefinition @'\r?\n(.*?)\r?\n'@")
    Check $match.Success 'Standalone console Job source found'
    Add-Type -TypeDefinition $match.Groups[1].Value
    Check ([bool]('CortivaReceiverConsole' -as [type])) 'Standalone kill-on-close Job owner compiles'
    function Get-ReleaseIslandProcesses{return @()}
    Check (-not(Test-ReleaseIslandOwner)) 'No island means launch is permitted'
    function Get-ReleaseIslandProcesses{return [pscustomobject]@{Path=(Join-Path $ReleaseRoot 'app/IslandDesktop.exe')}}
    Check (Test-ReleaseIslandOwner) 'Island from this package can be reused'
    function Get-ReleaseIslandProcesses{return [pscustomobject]@{Path='synthetic-other-package/IslandDesktop.exe'}}
    $rejected=$false;try{Test-ReleaseIslandOwner|Out-Null}catch{$rejected=$_.Exception.Message.Contains('Another Island Desktop package')}
    Check $rejected 'Other island package is refused before wallpaper activation'
    $result=@{pass=$true;checks=$count;scope='Isolated launcher ownership and restore contracts; native desktop/Lively not changed';nativeReceiverStarted=$false}
    [IO.File]::WriteAllText([IO.Path]::GetFullPath($Output),($result|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    $result|ConvertTo-Json -Compress
} finally {
    if($child){$child.Refresh();if(-not $child.HasExited){Stop-Process -Id $child.Id -ErrorAction SilentlyContinue}}
    $env:LOCALAPPDATA=$oldLocal
    # Only an explicitly created test directory under the system temp folder.
    if([IO.Path]::GetFullPath($temp).StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()))){Remove-Item -LiteralPath $temp -Recurse -Force}
}
