using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading;
using NAudio.CoreAudioApi;

namespace Island.Windows;

/// <summary>
/// Puts a browser's tab processes into Windows efficiency mode (EcoQoS + idle priority, as Task Manager does)
/// while the browser is not the foreground app, and restores them the moment it is. The browser main process,
/// GPU, network, storage and audio services are never touched; while the browser is playing sound its tabs only
/// get EcoQoS (no priority drop) so playback cannot stutter.
/// </summary>
public sealed class EcoMode : IDisposable
{
    private static readonly string[] Chromium = ["chrome", "msedge", "brave", "opera", "vivaldi"];
    private static readonly string[] Spared = ["--type=gpu-process", "audio.mojom", "network.mojom", "storage.mojom", "--type=crashpad-handler", "--type=broker"];
    private readonly Timer timer;
    private readonly Dictionary<int, uint> throttled = new(); // pid -> original priority class
    private readonly Dictionary<int, string> commandLines = new();
    private readonly object gate = new();
    private bool enabled, disposed;

    public event Action<int>? Changed;
    public int ThrottledCount { get { lock (gate) return throttled.Count; } }

    public EcoMode(bool enabled)
    {
        this.enabled = enabled;
        timer = new Timer(_ => Tick(), null, TimeSpan.FromSeconds(3), TimeSpan.FromSeconds(2));
    }

    public bool Enabled
    {
        get => enabled;
        set { enabled = value; if (!value) RestoreAll(); }
    }

    private void Tick()
    {
        if (disposed || !Monitor.TryEnter(gate)) return;
        try
        {
            string foreground = ForegroundProcessName();
            var alive = new HashSet<int>();
            HashSet<int>? audible = null;
            foreach (var name in Chromium.Append("firefox"))
            {
                var processes = Process.GetProcessesByName(name);
                if (processes.Length == 0) continue;
                bool background = enabled && !string.Equals(foreground, name, StringComparison.OrdinalIgnoreCase);
                bool playing = false;
                if (background) { audible ??= AudiblePids(); playing = processes.Any(p => audible.Contains(p.Id)); }
                foreach (var process in processes)
                {
                    using (process)
                    {
                        alive.Add(process.Id);
                        if (background && IsTab(name, process.Id)) Throttle(process.Id, keepPriority: playing);
                        else Restore(process.Id);
                    }
                }
            }
            // Forget processes that exited.
            foreach (var pid in throttled.Keys.Where(p => !alive.Contains(p)).ToList()) throttled.Remove(pid);
            foreach (var pid in commandLines.Keys.Where(p => !alive.Contains(p)).ToList()) commandLines.Remove(pid);
            Changed?.Invoke(throttled.Count);
        }
        catch (Exception error) { Log.Error("eco mode", error); }
        finally { Monitor.Exit(gate); }
    }

    private bool IsTab(string browser, int pid)
    {
        if (!commandLines.TryGetValue(pid, out var line)) commandLines[pid] = line = CommandLine(pid) ?? "";
        if (browser == "firefox") return line.Contains("-contentproc") && line.Contains(" tab");
        if (!line.Contains("--type=")) return false; // browser main process
        if (Spared.Any(s => line.Contains(s, StringComparison.OrdinalIgnoreCase))) return false;
        return line.Contains("--type=renderer") || line.Contains("--type=utility");
    }

    private void Throttle(int pid, bool keepPriority)
    {
        IntPtr handle = OpenProcess(ProcessSetInformation | ProcessQueryLimited, false, pid);
        if (handle == IntPtr.Zero) return;
        try
        {
            var state = new PowerThrottling { Version = 1, ControlMask = ExecutionSpeed, StateMask = ExecutionSpeed };
            SetProcessInformation(handle, ProcessPowerThrottlingClass, ref state, (uint)Marshal.SizeOf<PowerThrottling>());
            if (!throttled.ContainsKey(pid)) throttled[pid] = GetPriorityClass(handle);
            uint original = throttled[pid];
            SetPriorityClass(handle, keepPriority ? original : IdlePriority);
        }
        finally { CloseHandle(handle); }
    }

    private void Restore(int pid)
    {
        if (!throttled.TryGetValue(pid, out var original)) return;
        IntPtr handle = OpenProcess(ProcessSetInformation | ProcessQueryLimited, false, pid);
        if (handle != IntPtr.Zero)
        {
            try
            {
                // ControlMask 0 hands power management back to Windows/the browser.
                var state = new PowerThrottling { Version = 1, ControlMask = 0, StateMask = 0 };
                SetProcessInformation(handle, ProcessPowerThrottlingClass, ref state, (uint)Marshal.SizeOf<PowerThrottling>());
                if (original != 0) SetPriorityClass(handle, original);
            }
            finally { CloseHandle(handle); }
        }
        throttled.Remove(pid);
    }

    private void RestoreAll()
    {
        lock (gate) { foreach (var pid in throttled.Keys.ToList()) Restore(pid); }
        Changed?.Invoke(0);
    }

    private static HashSet<int> AudiblePids()
    {
        var pids = new HashSet<int>();
        try
        {
            using var enumerator = new MMDeviceEnumerator();
            using var device = enumerator.GetDefaultAudioEndpoint(DataFlow.Render, Role.Multimedia);
            var sessions = device.AudioSessionManager.Sessions;
            for (int i = 0; i < sessions.Count; i++) { using var session = sessions[i]; if (session.State == NAudio.CoreAudioApi.Interfaces.AudioSessionState.AudioSessionStateActive) pids.Add((int)session.GetProcessID); }
        }
        catch { }
        return pids;
    }

    private static string ForegroundProcessName()
    {
        GetWindowThreadProcessId(GetForegroundWindow(), out uint pid);
        try { using var process = Process.GetProcessById((int)pid); return process.ProcessName; } catch { return ""; }
    }

    /// <summary>Reads another same-user process's command line (ProcessCommandLineInformation).</summary>
    private static string? CommandLine(int pid)
    {
        IntPtr handle = OpenProcess(ProcessQueryLimited, false, pid);
        if (handle == IntPtr.Zero) return null;
        try
        {
            NtQueryInformationProcess(handle, 60, IntPtr.Zero, 0, out int size);
            if (size <= 0) return null;
            IntPtr buffer = Marshal.AllocHGlobal(size);
            try
            {
                if (NtQueryInformationProcess(handle, 60, buffer, size, out _) != 0) return null;
                ushort length = (ushort)Marshal.ReadInt16(buffer);
                IntPtr text = Marshal.ReadIntPtr(buffer, IntPtr.Size); // UNICODE_STRING.Buffer after Length/MaximumLength (+padding)
                return Marshal.PtrToStringUni(text, length / 2);
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }
        finally { CloseHandle(handle); }
    }

    public void Dispose()
    {
        if (disposed) return;
        disposed = true;
        timer.Dispose();
        RestoreAll();
    }

    private const int ProcessPowerThrottlingClass = 4;
    private const uint ExecutionSpeed = 0x1, IdlePriority = 0x40, ProcessSetInformation = 0x0200, ProcessQueryLimited = 0x1000;
    [StructLayout(LayoutKind.Sequential)] private struct PowerThrottling { public uint Version, ControlMask, StateMask; }
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool SetProcessInformation(IntPtr process, int infoClass, ref PowerThrottling info, uint size);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
    [DllImport("kernel32.dll")] private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] private static extern uint GetPriorityClass(IntPtr process);
    [DllImport("kernel32.dll")] private static extern bool SetPriorityClass(IntPtr process, uint priority);
    [DllImport("ntdll.dll")] private static extern int NtQueryInformationProcess(IntPtr process, int infoClass, IntPtr buffer, int length, out int returned);
    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint pid);
}
