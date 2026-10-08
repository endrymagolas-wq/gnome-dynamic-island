# Pause only this repository's offline Blender workers while a named game runs.
param([string[]]$GameProcess=@('cs2'))
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$stage=Join-Path $root 'wallpaper/assets/v6-stage'
$status=Join-Path $stage 'resource-guard.json'
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class ResortRenderControl {
 [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr window, out uint pid);
 [DllImport("kernel32.dll", SetLastError=true)] static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
 [DllImport("ntdll.dll")] static extern int NtSuspendProcess(IntPtr handle);
 [DllImport("ntdll.dll")] static extern int NtResumeProcess(IntPtr handle);
 public static int ForegroundPid() {uint pid;GetWindowThreadProcessId(GetForegroundWindow(),out pid);return (int)pid;}
 public static void SetPaused(int pid, bool pause) {
  var handle=OpenProcess(0x0800,false,pid);
  if(handle==IntPtr.Zero)throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
  try {int result=pause?NtSuspendProcess(handle):NtResumeProcess(handle);if(result!=0)throw new Exception("Process state change failed: "+result);}
  finally {CloseHandle(handle);}
 }
}
'@
$suspended=[System.Collections.Generic.HashSet[int]]::new()
function Owned($process){return $process -and $process.Name -eq 'blender.exe' -and $process.CommandLine -like ('*'+$root+'*') -and $process.CommandLine -like '*render_resort_v6.py*'}
try {
 while($true){
  if(Test-Path -LiteralPath (Join-Path $stage 'resource-guard-stop')){break}
  $games=@(Get-Process -Name $GameProcess -ErrorAction SilentlyContinue)
  $gameActive=@($games | Where-Object {$_.Id -eq [ResortRenderControl]::ForegroundPid()}).Count -gt 0
  $workers=@(Get-CimInstance Win32_Process -Filter "Name='blender.exe'" | Where-Object {Owned $_})
  if($gameActive){
   foreach($worker in $workers){if(-not $suspended.Contains([int]$worker.ProcessId)){
    [ResortRenderControl]::SetPaused([int]$worker.ProcessId,$true)
    $suspended.Add([int]$worker.ProcessId) | Out-Null
   }}
  } else {
   foreach($workerId in @($suspended)){
    $worker=Get-CimInstance Win32_Process -Filter ('ProcessId='+$workerId)
    if(Owned $worker){[ResortRenderControl]::SetPaused($workerId,$false)}
    $suspended.Remove($workerId) | Out-Null
   }
  }
  @{stage=if($gameActive){'paused-for-game'}else{'rendering'};ownedSuspendedPids=@($suspended);updatedAt=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $status
  $batch=Get-Content -LiteralPath (Join-Path $stage 'batch-progress.json') -Raw | ConvertFrom-Json
  if($batch.stage -eq 'complete'){break}
  Start-Sleep -Seconds 10
 }
} finally {
 foreach($workerId in @($suspended)){
  $worker=Get-CimInstance Win32_Process -Filter ('ProcessId='+$workerId)
  if(Owned $worker){[ResortRenderControl]::SetPaused($workerId,$false)}
 }
 @{stage='stopped';ownedSuspendedPids=@();updatedAt=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $status
}
