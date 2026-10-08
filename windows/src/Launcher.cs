// Windows .NET Framework bootstrap; does not require a globally installed modern .NET.
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
using System.Runtime.InteropServices;
using System.Threading;

internal static class Launcher
{
    [StructLayout(LayoutKind.Sequential)] private struct Rect { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] private struct AppBar { public int Size; public IntPtr Window; public uint Message, Edge; public Rect Rect; public IntPtr Param; }
    [DllImport("shell32.dll")] private static extern UIntPtr SHAppBarMessage(uint message, ref AppBar data);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] private static extern IntPtr FindWindow(string name,string title);
    [DllImport("user32.dll")] private static extern bool ShowWindowAsync(IntPtr window,int command);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll",EntryPoint="SetWindowLongPtrW")] private static extern IntPtr SetWindowLongPtr(IntPtr window,int index,IntPtr value);
    [DllImport("user32.dll")] private static extern bool SetLayeredWindowAttributes(IntPtr window,uint color,byte alpha,uint flags);
    private static void HideForRecovery(IntPtr window)
    {
        if(window==IntPtr.Zero)return;
        // Explorer owns these windows on another UI thread. Queue the hide
        // and confirm it instead of waiting synchronously inside ShowWindow.
        ShowWindowAsync(window,0);
        for(int attempt=0;attempt<50 && IsWindowVisible(window);attempt++)Thread.Sleep(10);
    }
    [STAThread]
    private static void Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string executable = Path.Combine(root, "app", "IslandDesktop.exe");
        string runtime = Path.Combine(root, "runtime");
        if (!File.Exists(executable) || !File.Exists(Path.Combine(runtime, "dotnet.exe")))
        {
            MessageBox.Show("Keep the app and runtime folders beside IslandDesktop.exe.", "Island Desktop");
            return;
        }
        try
        {
            var start = new ProcessStartInfo(executable) { UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = Path.GetDirectoryName(executable) };
            start.EnvironmentVariables["DOTNET_ROOT"] = runtime;
            start.EnvironmentVariables["DOTNET_ROOT_X64"] = runtime;
            using (var child = Process.Start(start))
            {
                child.WaitForExit();
                // Restore Explorer even if the UI process crashes or is ended in Task Manager.
                string data = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "IslandDesktopWindows");
                string owner = Path.Combine(data, "taskbar-owner.txt"), backup = Path.Combine(data, "taskbar-state.txt");
                int pid, state;
                if (File.Exists(owner) && int.TryParse(File.ReadAllText(owner), out pid) && pid == child.Id && File.Exists(backup) && int.TryParse(File.ReadAllText(backup), out state))
                {
                    var recovery=Stopwatch.StartNew();
                    string layer=Path.Combine(data,"tray-layer-state.txt");
                    if(File.Exists(layer))
                    {
                        string[] fields=File.ReadAllLines(layer);long style;uint color,flags;byte alpha;
                        if(fields.Length==4 && long.TryParse(fields[0],out style) && uint.TryParse(fields[1],out color) && byte.TryParse(fields[2],out alpha) && uint.TryParse(fields[3],out flags))
                        {
                            HideForRecovery(FindWindow("TopLevelWindowForOverflowXamlIsland",null));
                            HideForRecovery(FindWindow("NotifyIconOverflowWindow",null));
                            var window=FindWindow("Shell_TrayWnd",null);HideForRecovery(window);SetWindowLongPtr(window,-20,new IntPtr(style));
                            if((style&0x80000)!=0)SetLayeredWindowAttributes(window,color,alpha,flags);
                        }
                        File.Delete(layer);
                    }
                    var bar = new AppBar { Size = Marshal.SizeOf(typeof(AppBar)), Param = new IntPtr(state) };
                    SHAppBarMessage(10, ref bar);
                    string visibility=Path.Combine(data,"taskbar-visible.txt");
                    if(File.Exists(visibility)) { ShowWindowAsync(FindWindow("Shell_TrayWnd",null),File.ReadAllText(visibility)=="1"?8:0); File.Delete(visibility); }
                    File.Delete(backup); File.Delete(owner);
                    File.WriteAllText(Path.Combine(data,"taskbar-recovery-ms.txt"),recovery.ElapsedMilliseconds.ToString());
                }
            }
        }
        catch (Exception error) { MessageBox.Show(error.Message, "Island Desktop"); }
    }
}
