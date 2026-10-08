$ErrorActionPreference='Stop'
$ctl=Join-Path $PSScriptRoot 'control.ps1'
$checks=[Collections.Generic.List[object]]::new()
function State { & $ctl -Command status | ConvertFrom-Json }
function Check([bool]$condition,[string]$name) { $checks.Add(@{name=$name;passed=$condition}); if(-not $condition){throw "FAIL: $name"} }
function Ready {
    $deadline=[DateTime]::UtcNow.AddSeconds(12)
    do { try { $s=State; if($s.shell -and $s.shell.appCount -gt 0){return $s} } catch{}; Start-Sleep -Milliseconds 200 } while([DateTime]::UtcNow -lt $deadline)
    throw 'Shell did not initialize'
}
Add-Type @'
using System; using System.Runtime.InteropServices;
public static class TaskbarProbe {
 [StructLayout(LayoutKind.Sequential)] struct Rect {public int L,T,R,B;}
 [StructLayout(LayoutKind.Sequential)] struct Bar {public int Size; public IntPtr Window;public uint Message,Edge;public Rect Rect;public IntPtr Param;}
 [DllImport("shell32.dll")] static extern UIntPtr SHAppBarMessage(uint message,ref Bar bar);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern IntPtr FindWindow(string name,string title);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr window);
 public static bool Visible(){return IsWindowVisible(FindWindow("Shell_TrayWnd",null));}
 public static int State(){var b=new Bar{Size=Marshal.SizeOf<Bar>()};return (int)SHAppBarMessage(4,ref b).ToUInt32();}
}
'@
$backup=Join-Path $env:LOCALAPPDATA 'IslandDesktopWindows\taskbar-state.txt'
try {
    $s=Ready
    $original=$s.shell.originalTaskbarState
    $visible=$s.shell.originalTaskbarVisible
    Check (-not $s.shell.taskbarVisible) 'Native taskbar cannot compete with dock bottom-edge reveal'
    Check ($s.shell.appCount -gt 0) 'Dock enumerates real desktop applications'
    Check (($s.shell.taskbarState -band 1) -eq 1) 'Explorer taskbar uses recoverable auto-hide'
    & $ctl -Command panel | Out-Null
    Start-Sleep -Milliseconds 650
    $s=State
    Check ($s.shell.revealed -and $s.shell.panelWidth -gt 1000 -and $s.shell.panelHeight -eq 26) 'Top panel expands horizontally instead of opening the media card'
    Check (-not $s.expanded) 'Top panel leaves media popup closed'
    & $ctl -Command panel-snapshot -Path (Join-Path $PSScriptRoot 'verification\panel-v2.png') | Out-Null
    & $ctl -Command dock-snapshot -Path (Join-Path $PSScriptRoot 'verification\dock-v2.png') | Out-Null
    & $ctl -Command expand | Out-Null
    Start-Sleep -Milliseconds 650
    $s=State
    Check ($s.expanded -and -not $s.shell.revealed -and [Math]::Abs($s.width-380) -lt 1) 'Media popup excludes the expanded top panel'
    & $ctl -Command snapshot -Path (Join-Path $PSScriptRoot 'verification\media-v2.png') | Out-Null
    & $ctl -Command quit | Out-Null
    Start-Sleep -Seconds 1
    Check (([TaskbarProbe]::State()) -eq $original -and -not (Test-Path $backup)) 'Clean exit restores the exact Explorer taskbar state'
    Check (([TaskbarProbe]::Visible()) -eq $visible) 'Clean exit restores original taskbar visibility'
    & (Join-Path $PSScriptRoot 'start.ps1')
    $s=Ready
    Stop-Process -Id $s.pid
    $deadline=[DateTime]::UtcNow.AddSeconds(6)
    while((Test-Path $backup) -and [DateTime]::UtcNow -lt $deadline){Start-Sleep -Milliseconds 100}
    Check (([TaskbarProbe]::State()) -eq $original -and -not (Test-Path $backup)) 'Launcher restores Explorer after abrupt UI process termination'
    Check (([TaskbarProbe]::Visible()) -eq $visible) 'Crash watchdog restores original taskbar visibility'
} finally {
    & (Join-Path $PSScriptRoot 'start.ps1')
    $checks | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $PSScriptRoot 'verification\shell-checks.json')
}
Write-Output "PASS shell checks: $($checks.Count)"
