using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Win32;

namespace Island.Windows;

public record WallpaperStatus(bool Connected, string State, bool Paused, bool LivelyRunning);
public record WallpaperPreferences(bool Ready, bool Water, int Quality, int TimeOfDay);
public sealed class DesktopService
{
    private readonly HttpClient http = new() { Timeout = TimeSpan.FromSeconds(2) };
    public WallpaperStatus Wallpaper { get; private set; } = new(false, "", false, false);
    public WallpaperPreferences ReadWallpaperPreferences()
    {
        try
        {
            var file = FindWallpaperProperties();
            if (file == null) return new(false, true, 0, 0);
            using var json = JsonDocument.Parse(File.ReadAllText(file));
            return new(true, json.RootElement.GetProperty("water").GetProperty("value").GetBoolean(), json.RootElement.GetProperty("quality").GetProperty("value").GetInt32(), json.RootElement.GetProperty("timeOfDay").GetProperty("value").GetInt32());
        }
        catch { return new(false, true, 0, 0); }
    }
    private static string? FindWallpaperProperties()
    {
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        var roots = new System.Collections.Generic.List<string> { Path.Combine(local, "Lively Wallpaper") };
        var packages = Path.Combine(local, "Packages");
        if (Directory.Exists(packages)) roots.AddRange(Directory.GetDirectories(packages, "*Lively*").Select(p => Path.Combine(p, "LocalCache/Local/Lively Wallpaper")));
        foreach (var root in roots)
        {
            var layout = Path.Combine(root, "WallpaperLayout.json"); if (!File.Exists(layout)) continue;
            using var json = JsonDocument.Parse(File.ReadAllText(layout));
            foreach (var item in json.RootElement.EnumerateArray())
            {
                if (!item.GetProperty("LivelyScreen").GetProperty("IsPrimary").GetBoolean()) continue;
                if (!string.Equals(Path.GetFileName(item.GetProperty("LivelyInfoPath").GetString()), "resort-island-blender", StringComparison.OrdinalIgnoreCase)) continue;
                var index = item.GetProperty("LivelyScreen").GetProperty("Index").GetInt32();
                var file = Path.Combine(root, "Library/SaveData/wpdata/resort-island-blender", index.ToString(), "LivelyProperties.json");
                if (File.Exists(file)) return file;
            }
        }
        return null;
    }
    public async Task<bool> WallpaperProperty(string name, int value)
    {
        if (!ReadWallpaperPreferences().Ready || !(name == "water" && value is 0 or 1 || name == "quality" && value is >= 0 and <= 2 || name == "timeOfDay" && value is >= 0 and <= 4)) return false;
        try
        {
            string cli = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ResortIsland/lively-cli/Livelycu.exe");
            if (!File.Exists(cli)) return false;
            var start = new ProcessStartInfo(cli) { UseShellExecute = false, CreateNoWindow = true };
            start.ArgumentList.Add("setprop"); start.ArgumentList.Add("--property"); start.ArgumentList.Add(name + "=" + (name == "water" ? value == 1 ? "true" : "false" : value.ToString()));
            using var process = Process.Start(start)!;
            await process.WaitForExitAsync(); return process.ExitCode == 0;
        }
        catch (Exception e) { Log.Error("wallpaper property", e); return false; }
    }
    public async Task RefreshWallpaper()
    {
        bool lively = Process.GetProcessesByName("Lively").Any();
        try
        {
            using var response = await http.GetAsync("http://127.0.0.1:18765/events");
            response.EnsureSuccessStatusCode();
            using var json = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            Wallpaper = new(true, json.RootElement.GetProperty("state").GetString() ?? "idle", json.RootElement.GetProperty("paused").GetBoolean(), lively);
        }
        catch (Exception e) { Wallpaper = new(false, "", false, lively); Log.Error("wallpaper connection", e); }
    }
    public static bool StartupEnabled => Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run")?.GetValue("IslandDesktopWindows") != null;
    public static void SetStartup(bool enabled)
    {
        using var key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run");
        if (enabled)
        {
            var launcher = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "IslandDesktop.exe"));
            var desktop = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "start-desktop.ps1"));
            // Prefer the full desktop (wallpaper host + Lively + island); a headless console host avoids a flashing window.
            key.SetValue("IslandDesktopWindows", File.Exists(desktop)
                ? "conhost.exe --headless powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"" + desktop + "\""
                : "\"" + (File.Exists(launcher) ? launcher : Environment.ProcessPath) + "\"");
        }
        else key.DeleteValue("IslandDesktopWindows", false);
    }
    public static void Open(string uri)
    {
        try { Process.Start(new ProcessStartInfo(uri) { UseShellExecute = true }); }
        catch (Exception e) { Log.Error("open", e); }
    }
    public static void OpenLively()
    {
        // Use the already-running installation, including Microsoft Store path translation.
        try
        {
            using var process = Process.GetProcessesByName("Lively").FirstOrDefault();
            var executable = process?.MainModule?.FileName;
            if (executable != null) { Process.Start(new ProcessStartInfo(executable, "app --showApp true") { UseShellExecute = true }); return; }
        }
        catch (Exception e) { Log.Error("Lively launch", e); }
        Open("shell:AppsFolder");
    }
    public static void Browser(string site)
    {
        var url = site == "netflix" ? "https://www.netflix.com/browse" : "https://www.youtube.com/";
        string[] candidates = [Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Google/Chrome/Application/chrome.exe"), Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Microsoft/Edge/Application/msedge.exe"), Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Google/Chrome/Application/chrome.exe")];
        var browser = candidates.FirstOrDefault(File.Exists);
        if (browser == null) { Open(url); return; }
        Process.Start(new ProcessStartInfo(browser, "--app=" + url) { UseShellExecute = false });
    }

    [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] private static extern bool IsZoomed(IntPtr hwnd);
    [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr hwnd, out Rect rect);
    [DllImport("user32.dll")] private static extern IntPtr MonitorFromWindow(IntPtr hwnd, uint flags);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern bool GetMonitorInfo(IntPtr monitor, ref MonitorInfo info);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetClassName(IntPtr hwnd, System.Text.StringBuilder text, int count);
    [StructLayout(LayoutKind.Sequential)] private struct MonitorInfo { public int Size; public Rect Monitor, Work; public uint Flags; }
    public static bool Fullscreen(IntPtr ownWindow)
    {
        var foreground = GetForegroundWindow();
        if (foreground == IntPtr.Zero || foreground == ownWindow) return false;
        // Maximized captioned apps may cover the monitor rect when Explorer autohides.
        // They are not fullscreen games/video and must still expose the edge panel.
        if (IsZoomed(foreground) && (GetWindowLongPtr(foreground, -16).ToInt64() & 0x00C00000L) != 0) return false;
        if (MonitorFromWindow(foreground, 2) != MonitorFromWindow(ownWindow, 2)) return false;
        var name = new System.Text.StringBuilder(128); GetClassName(foreground, name, name.Capacity);
        if (name.ToString() is "Progman" or "WorkerW" or "Shell_TrayWnd") return false;
        var info = new MonitorInfo { Size = Marshal.SizeOf<MonitorInfo>() };
        if (!GetMonitorInfo(MonitorFromWindow(foreground, 2), ref info) || !GetWindowRect(foreground, out var rect)) return false;
        return rect.Left <= info.Monitor.Left && rect.Top <= info.Monitor.Top && rect.Right >= info.Monitor.Right && rect.Bottom >= info.Monitor.Bottom;
    }
    public static void NoActivate(IntPtr window)
    {
        var style = GetWindowLongPtr(window, -20).ToInt64();
        SetWindowLongPtr(window, -20, new IntPtr(style | 0x08000000L | 0x00000080L));
    }
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")] private static extern IntPtr GetWindowLongPtr(IntPtr hwnd, int index);
    [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW")] private static extern IntPtr SetWindowLongPtr(IntPtr hwnd, int index, IntPtr value);
}
