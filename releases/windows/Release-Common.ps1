# Portable release helpers. All paths resolve from the extracted package.
Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'
$ReleaseRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$ReleaseInfo = Get-Content -LiteralPath (Join-Path $ReleaseRoot 'release.json') -Raw | ConvertFrom-Json
function Get-ReleaseState {
    $sha=[System.Security.Cryptography.SHA256]::Create()
    try {$id=([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($ReleaseRoot.ToLowerInvariant())))).Replace('-','').Substring(0,12)} finally {$sha.Dispose()}
    $path=Join-Path $env:LOCALAPPDATA ('IslandDesktopRelease/'+$ReleaseInfo.version+'/'+$id)
    New-Item -ItemType Directory -Force -Path $path | Out-Null
    return $path
}
function Write-ReleaseJson([string]$Path,$Value) {
    [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
}
function Test-LoopbackPort([int]$Port) {
    $client=New-Object Net.Sockets.TcpClient
    try {$task=$client.ConnectAsync('127.0.0.1',$Port); if(-not $task.Wait(300)){return $false};return $client.Connected} catch{return $false} finally{$client.Dispose()}
}
function Get-ReleaseHostIdentity {
    try {return Invoke-RestMethod -Uri 'http://127.0.0.1:18765/wallpaper/release.json' -TimeoutSec 2} catch {return $null}
}
function Test-OwnedProcess($State,[string]$ExpectedExe,[string]$ExpectedScript) {
    try {
        $p=Get-Process -Id ([int]$State.pid) -ErrorAction Stop
        if($p.Path -ne $ExpectedExe -or $p.StartTime.ToUniversalTime().ToString('o') -ne $State.started){return $false}
        if($ExpectedScript){
            $cim=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.Id)
            if(-not $cim.CommandLine.Contains($ExpectedScript)){return $false}
        }
        return $true
    } catch {return $false}
}
function Start-ReleaseHost {
    $python=Join-Path $ReleaseRoot 'python/python.exe';$server=Join-Path $ReleaseRoot 'wallpaper/server.py'
    if(-not(Test-Path -LiteralPath $python) -or -not(Test-Path -LiteralPath $server)){throw 'This package does not contain the wallpaper runtime.'}
    if(Test-LoopbackPort 18765){
        $identity=Get-ReleaseHostIdentity
        if(-not $identity -or $identity.packageId -ne $ReleaseInfo.packageId){throw 'Another wallpaper host is using port 18765. Stop that package first; this launcher does not replace it.'}
        return
    }
    $state=Get-ReleaseState
    $child=Start-Process -FilePath $python -ArgumentList ('"'+$server+'"') -WorkingDirectory $ReleaseRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $state 'host.log') -RedirectStandardError (Join-Path $state 'host-error.log')
    Write-ReleaseJson (Join-Path $state 'host-owner.json') @{pid=$child.Id;started=$child.StartTime.ToUniversalTime().ToString('o');exe=$python;script=$server}
    for($i=0;$i -lt 50;$i++){
        Start-Sleep -Milliseconds 200
        if($child.HasExited){throw 'The wallpaper host exited. See the package local host-error.log.'}
        $identity=Get-ReleaseHostIdentity
        if($identity -and $identity.packageId -eq $ReleaseInfo.packageId){return}
    }
    if(-not $child.HasExited){$child.Kill()}
    throw 'The wallpaper host did not become ready within 10 seconds.'
}
function Stop-ReleaseHost {
    $file=Join-Path (Get-ReleaseState) 'host-owner.json'
    if(-not(Test-Path -LiteralPath $file)){return}
    $owner=Get-Content -LiteralPath $file -Raw | ConvertFrom-Json
    if(Test-OwnedProcess $owner (Join-Path $ReleaseRoot 'python/python.exe') (Join-Path $ReleaseRoot 'wallpaper/server.py')){Stop-Process -Id $owner.pid -ErrorAction Stop}
    Remove-Item -LiteralPath $file
}
function Find-ReleaseLively {
    $package=Get-AppxPackage '*LivelyWallpaper*' -ErrorAction SilentlyContinue | Select-Object -First 1
    if($package){
        $root=Join-Path $env:LOCALAPPDATA ('Packages/'+$package.PackageFamilyName+'/LocalCache/Local/Lively Wallpaper')
        return [pscustomobject]@{Exe=(Join-Path $package.InstallLocation 'Build/Lively.exe');Data=$root;Logical=(Join-Path $env:LOCALAPPDATA 'Lively Wallpaper');Store=$true}
    }
    $running=Get-Process Lively -ErrorAction SilentlyContinue | Select-Object -First 1
    if($running -and $running.Path -match 'WindowsApps'){
        $install=Split-Path (Split-Path $running.Path -Parent) -Parent;$parts=(Split-Path $install -Leaf).Split('_')
        if($parts.Count -ge 5){$family=$parts[0]+'_'+$parts[-1];$data=Join-Path $env:LOCALAPPDATA ('Packages/'+$family+'/LocalCache/Local/Lively Wallpaper');if(Test-Path -LiteralPath $data){return [pscustomobject]@{Exe=$running.Path;Data=$data;Logical=(Join-Path $env:LOCALAPPDATA 'Lively Wallpaper');Store=$true}}}
    }
    $candidates=@((Join-Path $env:LOCALAPPDATA 'Programs/Lively Wallpaper/Lively.exe'),(Join-Path $env:ProgramFiles 'Lively Wallpaper/Lively.exe'))
    if($running -and $running.Path){$candidates=@($running.Path)+$candidates}
    foreach($exe in $candidates){if(Test-Path -LiteralPath $exe){$data=Join-Path $env:LOCALAPPDATA 'Lively Wallpaper';return [pscustomobject]@{Exe=$exe;Data=$data;Logical=$data;Store=$false}}}
    return $null
}
function Invoke-ReleaseLively([string]$Arguments) {
    $exe=Join-Path $ReleaseRoot 'tools/lively-cli/Livelycu.exe'
    if(-not(Test-Path -LiteralPath $exe)){throw 'The packaged Lively command utility is missing.'}
    $p=Start-Process -FilePath $exe -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    if(-not $p.WaitForExit(15000)){throw 'Lively command did not finish within 15 seconds.'}
    if($p.ExitCode -ne 0){throw ('Lively command failed with exit code '+$p.ExitCode)}
}
function Start-ReleaseWallpaper([switch]$InstallHooks) {
    $lively=Find-ReleaseLively
    if(-not $lively){throw 'Install Lively Wallpaper first: https://www.rocksdanister.com/lively/ . Then run this launcher again.'}
    Start-ReleaseHost
    if($InstallHooks){& (Join-Path $ReleaseRoot 'python/python.exe') (Join-Path $ReleaseRoot 'assistant/claude_hook.py') --install;if($LASTEXITCODE -ne 0){throw 'Claude Code hook installation failed.'}}
    $state=Get-ReleaseState;$entry=Join-Path $lively.Data 'Library/wallpapers/resort-island-blender';$logical=Join-Path $lively.Logical 'Library/wallpapers/resort-island-blender';$layout=Join-Path $lively.Data 'WallpaperLayout.json'
    $backup=Join-Path $state 'previous-lively-layout.json'
    if(Test-Path -LiteralPath $layout){
        $before=@(Get-Content -LiteralPath $layout -Raw | ConvertFrom-Json)
        if(-not($before | Where-Object {$_.LivelyInfoPath -eq $logical}) -and -not(Test-Path -LiteralPath $backup)){Copy-Item -LiteralPath $layout -Destination $backup}
    } elseif(-not(Test-Path -LiteralPath $backup)){Write-ReleaseJson $backup @()}
    New-Item -ItemType Directory -Force -Path $entry | Out-Null
    Copy-Item -LiteralPath (Join-Path $ReleaseRoot 'wallpaper/LivelyInfo.json'),(Join-Path $ReleaseRoot 'wallpaper/bootstrap.html') -Destination $entry -Force
    . (Join-Path $ReleaseRoot 'wallpaper/sync-properties.ps1')
    Sync-ResortProperties (Join-Path $ReleaseRoot 'wallpaper/LivelyProperties.json') (Join-Path $entry 'LivelyProperties.json')
    # The island's existing media controls locate this official command utility here.
    $cliTarget=Join-Path $env:LOCALAPPDATA 'ResortIsland/lively-cli';New-Item -ItemType Directory -Force -Path $cliTarget | Out-Null
    Copy-Item -Path (Join-Path $ReleaseRoot 'tools/lively-cli/*') -Destination $cliTarget -Recurse -Force
    if(-not(Get-Process Lively -ErrorAction SilentlyContinue)){Start-Process -FilePath $lively.Exe -ArgumentList 'app --showApp false' -WindowStyle Hidden;Start-Sleep -Seconds 2}
    Invoke-ReleaseLively ('setwp --file "'+$logical+'"')
    for($i=0;$i -lt 25;$i++){
        Start-Sleep -Milliseconds 200
        if(Test-Path -LiteralPath $layout){$active=@(Get-Content -LiteralPath $layout -Raw | ConvertFrom-Json);if($active | Where-Object {$_.LivelyInfoPath -eq $logical}){Write-ReleaseJson (Join-Path $state 'wallpaper-owner.json') @{layout=$layout;entry=$logical};Write-Host 'Fairy Lagoon V7 is active in Lively.';return}}
    }
    throw 'Lively has not confirmed the wallpaper. Open Lively and choose Fairy Lagoon V7.'
}
function Restore-ReleaseWallpaper {
    $state=Get-ReleaseState;$ownerFile=Join-Path $state 'wallpaper-owner.json';$backup=Join-Path $state 'previous-lively-layout.json'
    if(-not(Test-Path -LiteralPath $ownerFile)){Stop-ReleaseHost;return}
    $owner=Get-Content -LiteralPath $ownerFile -Raw | ConvertFrom-Json
    if(Test-Path -LiteralPath $owner.layout){
        $current=@(Get-Content -LiteralPath $owner.layout -Raw | ConvertFrom-Json)
        $ours=@($current | Where-Object {$_.LivelyInfoPath -eq $owner.entry})
        # Restore only screens still displaying this package; leave later user changes alone.
        foreach($screen in $ours){
            $index=[int]$screen.LivelyScreen.Index
            Invoke-ReleaseLively ('closewp --monitor '+$index)
            if(Test-Path -LiteralPath $backup){
                $old=@(Get-Content -LiteralPath $backup -Raw | ConvertFrom-Json) | Where-Object {$_.LivelyScreen.DeviceId -eq $screen.LivelyScreen.DeviceId} | Select-Object -First 1
                if($old -and $old.LivelyInfoPath -ne $owner.entry){Invoke-ReleaseLively ('setwp --file "'+$old.LivelyInfoPath+'" --monitor '+$index)}
            }
        }
    }
    Remove-Item -LiteralPath $ownerFile
    if(Test-Path -LiteralPath $backup){Remove-Item -LiteralPath $backup}
    Stop-ReleaseHost
    Write-Host 'The package wallpaper is closed; the previous Lively entry or ordinary Windows wallpaper is restored.'
}
function Get-ReleaseDiagnostics {
    $checks=[ordered]@{version=$ReleaseInfo.version;component=$ReleaseInfo.component;architecture=$env:PROCESSOR_ARCHITECTURE;portable=$true}
    foreach($item in @{'island'='IslandDesktop.exe';'dotnet'='runtime/dotnet.exe';'python'='python/python.exe';'wallpaper'='wallpaper/server.py';'airplay'='receiver/bin/uxplay.exe';'livelyCLI'='tools/lively-cli/Livelycu.exe'}.GetEnumerator()){$checks[$item.Key]=Test-Path -LiteralPath (Join-Path $ReleaseRoot $item.Value)}
    $checks['livelyInstalled']=[bool](Find-ReleaseLively)
    return ($checks | ConvertTo-Json -Compress)
}
function Get-ReleaseIslandProcesses {return @(Get-Process IslandDesktop -ErrorAction SilentlyContinue)}
function Test-ReleaseIslandOwner {
    $running=@(Get-ReleaseIslandProcesses)
    $ownedPaths=@((Join-Path $ReleaseRoot 'IslandDesktop.exe'),(Join-Path $ReleaseRoot 'app/IslandDesktop.exe'))
    foreach($process in $running){if(-not $process.Path -or $process.Path -notin $ownedPaths){throw 'Another Island Desktop package is running. Close that island before starting this package.'}}
    return [bool]$running.Count
}
