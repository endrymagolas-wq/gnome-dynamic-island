param([switch]$Diagnose)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($PSScriptRoot);$receiver=Join-Path $root 'receiver';$exe=Join-Path $receiver 'bin/uxplay.exe'
if($Diagnose){
    @{component='airplay';version='0.4.0-beta.1';native=(Test-Path -LiteralPath $exe);plugins=(Test-Path -LiteralPath (Join-Path $receiver 'lib/gstreamer-1.0'));scanner=(Test-Path -LiteralPath (Join-Path $receiver 'libexec/gstreamer-1.0/gst-plugin-scanner.exe'));certificates=(Test-Path -LiteralPath (Join-Path $receiver 'etc/ssl/certs/ca-bundle.crt'));sources=(Test-Path -LiteralPath (Join-Path $receiver 'source/uxplay-3dbf7ce-source.zip'));pin='created locally at first start';livelyRequired=$false;dotnetRequired=$false} | ConvertTo-Json -Compress
    exit 0
}
if(-not(Test-Path -LiteralPath $exe)){throw 'The receiver runtime is missing. Extract the whole archive.'}
$busy=Get-NetTCPConnection -State Listen -LocalPort 7100,7101,7102 -ErrorAction SilentlyContinue
if($busy){throw 'An AirPlay receiver is already listening. Turn off AirPlay in Island Desktop or stop the other receiver first.'}
$state=Join-Path $env:LOCALAPPDATA 'CortivaAirPlayWindows';New-Item -ItemType Directory -Force -Path $state | Out-Null
$identity=Join-Path $state 'identity.txt';$pinFile=Join-Path $state 'pin.txt'
$rng=[Security.Cryptography.RandomNumberGenerator]::Create()
try {
    if(-not(Test-Path -LiteralPath $identity)){$bytes=New-Object byte[] 6;$rng.GetBytes($bytes);$bytes[0]=2;[IO.File]::WriteAllText($identity,([BitConverter]::ToString($bytes)).Replace('-',':'))}
    if(-not(Test-Path -LiteralPath $pinFile)){$bytes=New-Object byte[] 4;$rng.GetBytes($bytes);[IO.File]::WriteAllText($pinFile,([string](1000+[BitConverter]::ToUInt32($bytes,0)%9000)))}
} finally {$rng.Dispose()}
$mac=(Get-Content -LiteralPath $identity -Raw).Trim();$pin=(Get-Content -LiteralPath $pinFile -Raw).Trim()
if($mac -notmatch '^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$' -or $pin -notmatch '^[1-9][0-9]{3}$'){throw 'Local AirPlay identity or PIN is invalid. Remove only the local CortivaAirPlayWindows identity/PIN files to regenerate.'}
$cfg=Join-Path $state 'receiver.cfg';[IO.File]::WriteAllText($cfg,"# Cortiva standalone receiver`n")
$info=New-Object Diagnostics.ProcessStartInfo
$info.FileName=$exe;$info.WorkingDirectory=$state;$info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true;$info.RedirectStandardInput=$true
$arguments=@('-n','Cortiva Island','-nh','-p','7100','-m',$mac,'-s','1920x1080','-fps','30','-avdec','-as','wasapisink','-vs','d3d11videosink fullscreen-toggle-mode=6 fullscreen=false force-aspect-ratio=true','-nofreeze','-hls','2','-lang','uk:en','-ca',(Join-Path $state 'coverart.bin'),'-dacp',(Join-Path $state 'remote.txt'),'-key',(Join-Path $state 'receiver-key.pem'),'-rc',$cfg,'-pin',$pin,'-reg',(Join-Path $state 'paired-devices.txt'))
$info.Arguments=($arguments | ForEach-Object {'"'+$_+'"'}) -join ' '
$info.EnvironmentVariables['ISLAND_EVENTS']='1';$info.EnvironmentVariables['ISLAND_HLS_AUDIO_SINK']='wasapisink';$info.EnvironmentVariables['ISLAND_HLS_BUFFER_SECONDS']='5'
$info.EnvironmentVariables['PATH']=(Join-Path $receiver 'bin')+';'+$env:PATH
$info.EnvironmentVariables['GST_PLUGIN_SYSTEM_PATH']=Join-Path $receiver 'lib/gstreamer-1.0';$info.EnvironmentVariables['GST_PLUGIN_PATH']=''
$info.EnvironmentVariables['GST_PLUGIN_SCANNER']=Join-Path $receiver 'libexec/gstreamer-1.0/gst-plugin-scanner.exe';$info.EnvironmentVariables['GST_REGISTRY']=Join-Path $state 'registry-1.28.bin'
$info.EnvironmentVariables['GSETTINGS_SCHEMA_DIR']=Join-Path $receiver 'share/glib-2.0/schemas';$info.EnvironmentVariables['GIO_MODULE_DIR']=Join-Path $receiver 'lib/gio/modules'
$info.EnvironmentVariables['SSL_CERT_FILE']=Join-Path $receiver 'etc/ssl/certs/ca-bundle.crt';$info.EnvironmentVariables['UXPLAYRC']=$cfg
# A kill-on-close Job prevents a receiver surviving its console owner.
Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
public static class CortivaReceiverConsole {
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr a,string n);
 [DllImport("kernel32.dll")] static extern bool SetInformationJobObject(IntPtr j,int c,IntPtr p,uint size);
 [DllImport("kernel32.dll")] static extern bool AssignProcessToJobObject(IntPtr j,IntPtr p);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
 [StructLayout(LayoutKind.Sequential)] struct Limits { public long t1,t2; public uint flags; public UIntPtr min,max; public uint active; public UIntPtr affinity; public uint priority,scheduling; }
 [StructLayout(LayoutKind.Sequential)] struct Io { public ulong a,b,c,d,e,f; }
 [StructLayout(LayoutKind.Sequential)] struct Extended { public Limits basic; public Io io; public UIntPtr process,job,peakProcess,peakJob; }
 public static int Run(ProcessStartInfo info) {
   IntPtr job=CreateJobObject(IntPtr.Zero,null);
   if(job==IntPtr.Zero) throw new InvalidOperationException("Cannot create receiver job.");
   var limits=new Extended();limits.basic.flags=0x2000;
   int size=Marshal.SizeOf(typeof(Extended));IntPtr ptr=Marshal.AllocHGlobal(size);
   try {Marshal.StructureToPtr(limits,ptr,false);if(!SetInformationJobObject(job,9,ptr,(uint)size))throw new InvalidOperationException("Cannot configure receiver job.");}
   finally {Marshal.FreeHGlobal(ptr);}
   using(var p=new Process()) {
     p.StartInfo=info;
     p.OutputDataReceived+=(s,e)=>{};p.ErrorDataReceived+=(s,e)=>{};
     try {
       p.Start();if(!AssignProcessToJobObject(job,p.Handle)){p.Kill();throw new InvalidOperationException("Cannot attach receiver job.");}
       p.BeginOutputReadLine();p.BeginErrorReadLine();p.WaitForExit();return p.ExitCode;
     } finally {CloseHandle(job);}
   }
 }
}
'@
Write-Host 'Cortiva Island - standalone AirPlay receiver'
Write-Host ('PIN: '+$pin) -ForegroundColor Cyan
Write-Host 'Choose Cortiva Island from AirPlay on your iPhone/iPad/Mac in the same local network.'
Write-Host 'Music and supported non-DRM AirPlay video open on this PC. Close this console to stop.'
Write-Host 'If the device cannot discover it, run Enable-AirPlay-Firewall.ps1 explicitly as administrator.'
$code=[CortivaReceiverConsole]::Run($info)
if($code -ne 0){throw ('The receiver exited with code '+$code+'. Check that no other receiver is running and that the local firewall permits AirPlay.')}
