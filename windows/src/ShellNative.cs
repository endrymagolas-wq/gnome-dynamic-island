using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Island.Windows;

public record ShellApp(IntPtr Handle, string Name, string Path, ImageSource? Icon, string Title, string AppId = "")
{
    public bool TopBarOnly => Path.Contains("OpenAI.ChatGPT-Desktop_",StringComparison.OrdinalIgnoreCase) || AppId.StartsWith("OpenAI.ChatGPT-Desktop_",StringComparison.OrdinalIgnoreCase);
}
public static class ShellNative
{
    [StructLayout(LayoutKind.Sequential)] public struct Point { public int X, Y; }
    [StructLayout(LayoutKind.Sequential)] private struct AppBar { public int Size; public IntPtr Window; public uint Message, Edge; public DesktopService.Rect Rect; public IntPtr Param; }
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out Point point);
    [DllImport("user32.dll")] public static extern short GetAsyncKeyState(int key);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr window, out DesktopService.Rect rect);
    private delegate bool EnumWindowCallback(IntPtr window, IntPtr data);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowCallback callback, IntPtr data);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr window);
    [DllImport("user32.dll")] private static extern bool ShowWindowAsync(IntPtr window, int command);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] private static extern IntPtr FindWindow(string name,string? title);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] private static extern int GetClassName(IntPtr window,StringBuilder name,int count);
    public static bool IsDesktopSurface(IntPtr window) { var name=new StringBuilder(64); GetClassName(window,name,name.Capacity); return name.ToString() is "Progman" or "WorkerW" or "Shell_TrayWnd" or "Shell_SecondaryTrayWnd"; }
    [DllImport("user32.dll")] private static extern bool SetWindowPos(IntPtr window,IntPtr after,int x,int y,int width,int height,uint flags);
    public static bool TaskbarVisible => IsWindowVisible(FindWindow("Shell_TrayWnd",null));
    public static void ShowTaskbar(bool visible) { var window=FindWindow("Shell_TrayWnd",null); if(window!=IntPtr.Zero) ShowWindowAsync(window,visible?8:0); }
    public static void Raise(IntPtr window) => SetWindowPos(window,new IntPtr(-1),0,0,0,0,0x13);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr window);
    [DllImport("user32.dll")] private static extern IntPtr GetWindow(IntPtr window, uint command);
    [DllImport("user32.dll", EntryPoint="GetWindowLongPtrW")] private static extern IntPtr GetStyle(IntPtr window, int index);
    [DllImport("user32.dll", EntryPoint="SetWindowLongPtrW")] private static extern IntPtr SetStyle(IntPtr window,int index,IntPtr value);
    public static void ToolWindow(IntPtr window) => SetStyle(window,-20,new IntPtr(GetStyle(window,-20).ToInt64()|0x80));
    public static void Inspectable(IntPtr window,bool inspect) => SetStyle(window,-20,new IntPtr(inspect?(GetStyle(window,-20).ToInt64()&~0x80L)|0x40000L:(GetStyle(window,-20).ToInt64()|0x80L)&~0x40000L));
    public static void ClickActivates(IntPtr window) => SetStyle(window,-20,new IntPtr(GetStyle(window,-20).ToInt64()&~0x08000000L));
    public static bool Owns(IntPtr window) { GetWindowThreadProcessId(window,out uint pid);return pid==Environment.ProcessId; }
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetWindowText(IntPtr window, StringBuilder text, int length);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint pid);
    [DllImport("user32.dll")] private static extern IntPtr GetKeyboardLayout(uint thread);
    [DllImport("user32.dll")] private static extern int GetKeyboardLayoutList(int count,[Out] IntPtr[]? layouts);
    [DllImport("user32.dll")] private static extern bool PostMessage(IntPtr window,uint message,IntPtr wparam,IntPtr lparam);
    public record KeyboardLayout(IntPtr Handle,string Name);
    public static KeyboardLayout[] Layouts() { var layouts=new IntPtr[GetKeyboardLayoutList(0,null)];GetKeyboardLayoutList(layouts.Length,layouts);return layouts.Select(h=>new KeyboardLayout(h,CultureInfo.GetCultureInfo((int)(h.ToInt64()&0xffff)).NativeName)).ToArray(); }
    public static void SetLayout(IntPtr window,IntPtr layout) { SetForegroundWindow(window);PostMessage(window,0x50,IntPtr.Zero,layout); }
    [DllImport("dwmapi.dll")] private static extern int DwmGetWindowAttribute(IntPtr window, uint attribute, out int value, int size);
    [DllImport("shell32.dll")] private static extern UIntPtr SHAppBarMessage(uint message, ref AppBar data);
    [DllImport("user32.dll")] private static extern void keybd_event(byte key, byte scan, uint flags, UIntPtr extra);
    private static readonly Dictionary<string, string> names = new(StringComparer.OrdinalIgnoreCase);
    private static readonly Dictionary<string, ImageSource?> icons = new(StringComparer.OrdinalIgnoreCase);
    public static string ForegroundTitle { get { var b = new StringBuilder(256); GetWindowText(GetForegroundWindow(), b, b.Capacity); return b.ToString(); } }
    public static string Language { get { try { var thread = GetWindowThreadProcessId(GetForegroundWindow(), out _); return CultureInfo.GetCultureInfo((int)(GetKeyboardLayout(thread).ToInt64() & 0xffff)).TwoLetterISOLanguageName.ToUpperInvariant(); } catch { return "⌨"; } } }
    public static List<ShellApp> Apps()
    {
        var result = new List<ShellApp>();
        EnumWindows((window, _) => {
            if (!IsWindowVisible(window) || IsDesktopSurface(window) || GetWindow(window, 4) != IntPtr.Zero || (GetStyle(window, -20).ToInt64() & 0x80) != 0) return true;
            DwmGetWindowAttribute(window, 14, out int cloaked, 4); if (cloaked != 0) return true;
            GetWindowThreadProcessId(window, out uint pid); if (pid == Environment.ProcessId) return true;
            var title = new StringBuilder(256); GetWindowText(window, title, title.Capacity); if (title.Length == 0) return true;
            try {
                using var p = Process.GetProcessById((int)pid);
                var path = p.MainModule?.FileName ?? "";
                if (p.ProcessName is "seelen-ui" or "Lively" or "Lively.Player.WebView2") return true;
                var name = p.ProcessName;
                if (path.Length > 0) { if(!names.TryGetValue(path,out var cached)) { cached=FileVersionInfo.GetVersionInfo(path).ProductName ?? name; names[path]=cached; } name=cached; }
                string appId = DockCatalog.WindowAppId(window, pid);
                if (appId.StartsWith("OpenAI.Codex_",StringComparison.OrdinalIgnoreCase) || path.Contains("OpenAI.Codex_",StringComparison.OrdinalIgnoreCase)) name="Codex";
                else if (appId.StartsWith("OpenAI.ChatGPT-Desktop_",StringComparison.OrdinalIgnoreCase) || path.Contains("OpenAI.ChatGPT-Desktop_",StringComparison.OrdinalIgnoreCase)) name="ChatGPT Classic";
                else if (Path.GetFileName(path).Equals("explorer.exe",StringComparison.OrdinalIgnoreCase)) name="Файли";
                result.Add(new(window, name, path, Icon(path), title.ToString(), appId));
            } catch { }
            return true;
        }, IntPtr.Zero);
        return result;
    }
    public static ImageSource? Icon(string path)
    {
        if (icons.TryGetValue(path, out var value)) return value;
        try { using var icon = System.Drawing.Icon.ExtractAssociatedIcon(path); if (icon != null) { value = Imaging.CreateBitmapSourceFromHIcon(icon.Handle, Int32Rect.Empty, BitmapSizeOptions.FromWidthAndHeight(32,32)); value.Freeze(); } } catch { }
        icons[path] = value; return value;
    }
    public static void Switch(IntPtr window)
    {
        if (window == GetForegroundWindow()) ShowWindowAsync(window, 6);
        else { if (IsIconic(window)) ShowWindowAsync(window, 9); SetForegroundWindow(window); }
    }
    public static void Shortcut(byte key)
    {
        keybd_event(0x5B,0,0,UIntPtr.Zero); keybd_event(key,0,0,UIntPtr.Zero);
        keybd_event(key,0,2,UIntPtr.Zero); keybd_event(0x5B,0,2,UIntPtr.Zero);
    }
    public static void StartMenu() { keybd_event(0x5B,0,0,UIntPtr.Zero); keybd_event(0x5B,0,2,UIntPtr.Zero); }
    public static int TaskbarState { get { var data = new AppBar { Size = Marshal.SizeOf<AppBar>() }; return (int)SHAppBarMessage(4,ref data).ToUInt32(); } }
    public static void SetTaskbar(int state) { var data = new AppBar { Size = Marshal.SizeOf<AppBar>(), Param = new IntPtr(state) }; SHAppBarMessage(10,ref data); }
}

// A time-based edge intent model shared by live cursor polling and deterministic tests.
public sealed class EdgeIntent
{
    private DateTimeOffset? entered, departed;
    public bool Revealed { get; private set; }
    public bool Update(bool edge, bool inside, bool blocked, DateTimeOffset now)
    {
        if (blocked) { entered = departed = null; return Revealed = false; }
        if (!Revealed) {
            if (!edge) entered = null;
            else { entered ??= now; if ((now-entered.Value).TotalMilliseconds >= 300) { Revealed = true; departed = null; } }
        } else if (inside || edge) departed = null;
        else { departed ??= now; if ((now-departed.Value).TotalMilliseconds >= 600) { Revealed = false; entered = departed = null; } }
        return Revealed;
    }
}
