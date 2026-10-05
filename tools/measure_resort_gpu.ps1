param([string]$ProcessIds,[int]$Seconds=30,[string]$OutputFile,[string]$ReadyFile)
$ErrorActionPreference='Stop'
$targetIds=@($ProcessIds.Split(',') | ForEach-Object {[int]$_})
$rows=@()
Get-Counter -Counter '\GPU Engine(*)\Utilization Percentage','\GPU Process Memory(*)\Dedicated Usage','\GPU Process Memory(*)\Shared Usage' -SampleInterval 1 -MaxSamples $Seconds -ErrorAction SilentlyContinue | ForEach-Object {
    if($ReadyFile -and $rows.Count -eq 0){[DateTime]::UtcNow.ToString('o') | Set-Content -LiteralPath $ReadyFile}
    $engines=@{};$memory=0;$sharedMemory=0;$invalidTargets=0
    foreach($sample in $_.CounterSamples) {
        if($sample.InstanceName -match '^pid_(\d+)_' -and $targetIds -contains [int]$Matches[1]) {
            if($sample.Status -ne 0){$invalidTargets++;continue}
            if($sample.Path -like '*dedicated usage') {$memory+=$sample.CookedValue}
            elseif($sample.Path -like '*shared usage') {$sharedMemory+=$sample.CookedValue}
            elseif($sample.InstanceName -match 'engtype_(.+)$') {
                $key=$Matches[1];$engines[$key]+=$sample.CookedValue
            }
        }
    }
    $rows+=@{timestamp=$_.Timestamp.ToUniversalTime().ToString('o');dedicatedMiB=$memory/1MB;sharedMiB=$sharedMemory/1MB;engines=$engines;invalidTargetSamples=$invalidTargets}
}
if($rows.Count -lt $Seconds-1){throw 'GPU counters did not provide the requested samples'}
@{scope='Windows per-process GPU counters for owned Lively player descendants';processIds=$targetIds;samples=$rows} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputFile -Encoding UTF8
