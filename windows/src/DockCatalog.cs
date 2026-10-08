using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Island.Windows;

public sealed record DockPin(string Id, string Name, string Launch, string Target, ImageSource? Icon)
{
    public bool TopBarOnly => Id.StartsWith("OpenAI.ChatGPT-Desktop_", StringComparison.OrdinalIgnoreCase) || Target.Contains("OpenAI.ChatGPT-Desktop_", StringComparison.OrdinalIgnoreCase);
    public bool Matches(ShellApp app)
    {
        if (app.TopBarOnly || TopBarOnly) return false;
        if (Id.Length > 0 && app.AppId.Length > 0 && Id.Equals(app.AppId, StringComparison.OrdinalIgnoreCase)) return true;
        // Chrome web apps share the browser executable but have independent identities.
        if (app.AppId.Contains("._crx_", StringComparison.OrdinalIgnoreCase) && !Id.Equals(app.AppId, StringComparison.OrdinalIgnoreCase)) return false;
        if (Id.Contains("!", StringComparison.Ordinal) || Id.Contains("._crx_", StringComparison.OrdinalIgnoreCase)) return false;
        if (Target.Length == 0) return false;
        if (Target.Equals(app.Path, StringComparison.OrdinalIgnoreCase)) return true;
        // Some launchers (Docker) hand their window to an executable inside
        // their own install directory. Never group by display name alone.
        string? directory = Path.GetDirectoryName(Target);
        return directory is { Length: > 0 } && Path.GetFileName(Target).Equals(Path.GetFileName(app.Path), StringComparison.OrdinalIgnoreCase)
            && app.Path.StartsWith(directory.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
    }
}

public sealed record DockEntry(string Id, string Name, ImageSource? Icon, DockPin? Pin, ShellApp[] Windows)
{
    public bool Running => Windows.Length > 0;
}

public static class DockCatalog
{
    private static readonly string[] Defaults = { "File Explorer", "Google Chrome", "YouTube Music", "Netflix", "Crunchyroll", "MiniMax Code", "Visual Studio Code", "ChatGPT", "Antigravity", "Claude", "Docker Desktop" };
    public static IReadOnlyList<string> RequestedNames => Defaults;
    public static List<DockPin> Load()
    {
        var installed = new Dictionary<string, (string Id, string Name)>(StringComparer.OrdinalIgnoreCase);
        var links = new Dictionary<string, (string Link, string Target)>(StringComparer.OrdinalIgnoreCase);
        object? shell = null, folder = null, items = null, wsh = null;
        try
        {
            shell = Activator.CreateInstance(Type.GetTypeFromProgID("Shell.Application")!);
            folder = ((dynamic)shell!).Namespace("shell:AppsFolder"); items = ((dynamic)folder).Items();
            foreach (object item in (dynamic)items)
            {
                try
                {
                    string name = ((dynamic)item).Name, id = ((dynamic)item).Path;
                    if (Defaults.Contains(name, StringComparer.OrdinalIgnoreCase) && !id.StartsWith("OpenAI.ChatGPT-Desktop_", StringComparison.OrdinalIgnoreCase))
                        if (!installed.ContainsKey(name) || id.StartsWith("OpenAI.Codex_", StringComparison.OrdinalIgnoreCase)) installed[name] = (id, name);
                }
                finally { if (Marshal.IsComObject(item)) Marshal.ReleaseComObject(item); }
            }
            wsh = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell")!);
            var directories = new[] { Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), @"Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"), Environment.GetFolderPath(Environment.SpecialFolder.Programs), Environment.GetFolderPath(Environment.SpecialFolder.CommonPrograms) };
            foreach (string directory in directories.Where(Directory.Exists))
                foreach (string file in Directory.EnumerateFiles(directory, "*.lnk", SearchOption.AllDirectories))
                {
                    string name = Path.GetFileNameWithoutExtension(file);
                    if (!Defaults.Contains(name, StringComparer.OrdinalIgnoreCase) || links.ContainsKey(name)) continue;
                    object shortcut = ((dynamic)wsh!).CreateShortcut(file);
                    try { links[name] = (file, (string)((dynamic)shortcut).TargetPath); }
                    finally { Marshal.ReleaseComObject(shortcut); }
                }
            var pins = new List<DockPin>();
            foreach (string requested in Defaults)
            {
                installed.TryGetValue(requested, out var app); links.TryGetValue(requested, out var link);
                string launch = link.Link ?? (app.Id is { Length: > 0 } ? "shell:AppsFolder\\" + app.Id : "");
                if (launch.Length == 0) continue;
                string name = requested == "ChatGPT" ? "Codex" : requested == "File Explorer" ? "Файли" : requested;
                string target = link.Target ?? "";
                if (requested == "File Explorer") target = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "explorer.exe");
                var pin = new DockPin(app.Id ?? target, name, launch, target, ShellImage(launch) ?? ShellNative.Icon(target));
                if (!pin.TopBarOnly) pins.Add(pin);
            }
            return pins;
        }
        finally
        {
            foreach (object? value in new[] { items, folder, shell, wsh }) if (value != null && Marshal.IsComObject(value)) Marshal.ReleaseComObject(value);
        }
    }
    public static DockEntry[] Merge(IEnumerable<DockPin> pins, IEnumerable<ShellApp> running)
    {
        var available = running.Where(app => !app.TopBarOnly).ToList(); var entries = new List<DockEntry>();
        foreach (var pin in pins.Where(pin => !pin.TopBarOnly).DistinctBy(pin => pin.Id, StringComparer.OrdinalIgnoreCase))
        {
            var windows = available.Where(pin.Matches).ToArray(); available.RemoveAll(pin.Matches);
            entries.Add(new(pin.Id, pin.Name, pin.Icon ?? windows.FirstOrDefault()?.Icon, pin, windows));
        }
        foreach (var group in available.GroupBy(app => app.AppId.Length > 0 ? app.AppId : app.Path.Length > 0 ? app.Path : app.Name, StringComparer.OrdinalIgnoreCase).OrderBy(g => g.Key, StringComparer.OrdinalIgnoreCase))
        {
            var first = group.First(); entries.Add(new(group.Key, first.Name, first.Icon, null, group.ToArray()));
        }
        return entries.ToArray();
    }
    public static void Launch(DockPin pin) => Process.Start(new ProcessStartInfo(pin.Launch) { UseShellExecute = true });
    public static string WindowAppId(IntPtr window, uint processId)
    {
        string windowId = ExplicitWindowAppId(window);
        if (windowId.Length > 0) return windowId;
        IntPtr process = OpenProcess(0x1000, false, processId);
        if (process == IntPtr.Zero) return "";
        try
        {
            uint length = 0;
            if (GetApplicationUserModelId(process, ref length, null) != 122 || length == 0 || length > 1024) return "";
            var result = new StringBuilder((int)length);
            return GetApplicationUserModelId(process, ref length, result) == 0 ? result.ToString() : "";
        }
        finally { CloseHandle(process); }
    }
    private static string ExplicitWindowAppId(IntPtr window)
    {
        IPropertyStore? store = null;
        try
        {
            Guid iid = typeof(IPropertyStore).GUID;
            if (SHGetPropertyStoreForWindow(window, ref iid, out store) != 0) return "";
            var key = new PropertyKey { Format = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), Id = 5 };
            if (store.GetValue(ref key, out var value) != 0) return "";
            try { return value.Type == 31 && value.Pointer != IntPtr.Zero ? Marshal.PtrToStringUni(value.Pointer) ?? "" : ""; }
            finally { PropVariantClear(ref value); }
        }
        catch (COMException) { return ""; }
        finally { if (store != null) Marshal.ReleaseComObject(store); }
    }
    private static ImageSource? ShellImage(string parsingName)
    {
        IImageFactory? factory = null; IntPtr bitmap = IntPtr.Zero;
        try
        {
            Guid iid = typeof(IImageFactory).GUID;
            if (SHCreateItemFromParsingName(parsingName, IntPtr.Zero, ref iid, out factory) != 0 || factory.GetImage(new Size { Width = 64, Height = 64 }, 4, out bitmap) != 0) return null;
            var image = Imaging.CreateBitmapSourceFromHBitmap(bitmap, IntPtr.Zero, Int32Rect.Empty, BitmapSizeOptions.FromEmptyOptions()); image.Freeze(); return image;
        }
        catch (Exception error) when (error is COMException or ArgumentException) { return null; }
        finally { if (bitmap != IntPtr.Zero) DeleteObject(bitmap); if (factory != null) Marshal.ReleaseComObject(factory); }
    }
    [StructLayout(LayoutKind.Sequential)] private struct Size { public int Width, Height; }
    [StructLayout(LayoutKind.Sequential)] private struct PropertyKey { public Guid Format; public uint Id; }
    [StructLayout(LayoutKind.Explicit, Size = 24)] private struct PropVariant { [FieldOffset(0)] public ushort Type; [FieldOffset(8)] public IntPtr Pointer; }
    [ComImport, Guid("bcc18b79-ba16-442f-80c4-8a59c30c463b"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IImageFactory { [PreserveSig] int GetImage(Size size, uint flags, out IntPtr bitmap); }
    [ComImport, Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IPropertyStore
    {
        [PreserveSig] int GetCount(out uint count);
        [PreserveSig] int GetAt(uint index, out PropertyKey key);
        [PreserveSig] int GetValue(ref PropertyKey key, out PropVariant value);
        [PreserveSig] int SetValue(ref PropertyKey key, ref PropVariant value);
        [PreserveSig] int Commit();
    }
    [DllImport("shell32.dll", CharSet = CharSet.Unicode)] private static extern int SHCreateItemFromParsingName(string name, IntPtr bindContext, ref Guid iid, out IImageFactory factory);
    [DllImport("shell32.dll")] private static extern int SHGetPropertyStoreForWindow(IntPtr window, ref Guid iid, out IPropertyStore store);
    [DllImport("ole32.dll")] private static extern int PropVariantClear(ref PropVariant value);
    [DllImport("gdi32.dll")] private static extern bool DeleteObject(IntPtr value);
    [DllImport("kernel32.dll")] private static extern IntPtr OpenProcess(uint access, bool inherit, uint processId);
    [DllImport("kernel32.dll")] private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] private static extern int GetApplicationUserModelId(IntPtr process, ref uint length, StringBuilder? appId);
}
