"""Verify the actual standalone console Job kills its child on owner exit.

Uses a sleeping PowerShell fixture, never starts UxPlay or advertises AirPlay.
"""
import argparse,json,os,re,subprocess,tempfile,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--script',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    text=a.script.read_text();source=re.search(r"Add-Type -TypeDefinition @'\r?\n(.*?)\r?\n'@",text,re.S).group(1)
    shell=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe';checks=0
    with tempfile.TemporaryDirectory(prefix='cortiva-receiver-owner-') as tmp:
        root=Path(tmp);pid_file=root/'fixture.pid';child_file=root/'child.ps1';owner_file=root/'owner.ps1'
        # PID is written only to an owned synthetic test directory.
        child_file.write_text("[IO.File]::WriteAllText('"+str(pid_file).replace("'","''")+"',[string]$PID)\nStart-Sleep -Seconds 120\n")
        owner_file.write_text("$ErrorActionPreference='Stop'\nAdd-Type -TypeDefinition @'\n"+source+"\n'@\n$info=New-Object Diagnostics.ProcessStartInfo\n$info.FileName='"+str(shell)+"'\n$info.Arguments='-NoProfile -ExecutionPolicy Bypass -File \""+str(child_file)+"\"'\n$info.UseShellExecute=$false\n$info.CreateNoWindow=$true\n$info.RedirectStandardOutput=$true\n$info.RedirectStandardError=$true\n$info.RedirectStandardInput=$true\n[CortivaReceiverConsole]::Run($info)\n")
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        owner=subprocess.Popen([str(shell),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(owner_file)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags)
        child_pid=None
        try:
            for _ in range(200):
                if pid_file.exists():break
                if owner.poll() is not None:raise RuntimeError(owner.stderr.read().decode(errors='replace'))
                time.sleep(.05)
            assert pid_file.exists(),'Job child did not start';checks+=1
            child_pid=int(pid_file.read_text())
            import ctypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.restype=ctypes.c_void_p
            handle=kernel.OpenProcess(0x100000,False,child_pid)
            assert handle,'Cannot inspect owned test process';checks+=1
            try:
                assert kernel.WaitForSingleObject(ctypes.c_void_p(handle),0)==258,'Child was already stopped';checks+=1
                owner.terminate();owner.wait(timeout=10)
                assert kernel.WaitForSingleObject(ctypes.c_void_p(handle),5000)==0,'Receiver Job child survived owner termination';checks+=1
            finally:kernel.CloseHandle(ctypes.c_void_p(handle))
        finally:
            if owner.poll() is None:owner.kill();owner.wait(timeout=10)
    result={'pass':True,'checks':checks,'scope':'Actual standalone kill-on-close Job owner with synthetic sleeping child; UxPlay/AirPlay never started'}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
