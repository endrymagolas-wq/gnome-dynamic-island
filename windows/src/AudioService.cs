using System;
using System.Collections.Generic;
using System.Diagnostics;
using NAudio.CoreAudioApi;
using NAudio.CoreAudioApi.Interfaces;
using NAudio.Wave;

namespace Island.Windows;

public record AppVolume(int Pid, string Name, float Volume, bool Muted);
public record AudioSnapshot(bool Available, string Device, float Volume, bool Muted, AppVolume[] Apps);
public sealed class AudioService : IDisposable
{
    private readonly MMDeviceEnumerator enumerator = new();
    // Opening the default endpoint and reading its name costs ~150 ms of COM work; doing that every second froze
    // the UI thread (visible as stutter in the island, top panel and dock). Keep it open and reopen it only when
    // Windows reports a different default device.
    private MMDevice? device;
    private volatile bool deviceStale = true;
    private DeviceWatcher? watcher;
    private MMDevice Device()
    {
        if (watcher == null) { watcher = new DeviceWatcher(() => deviceStale = true); try { enumerator.RegisterEndpointNotificationCallback(watcher); } catch { } }
        if (deviceStale || device == null)
        {
            device?.Dispose();
            device = enumerator.GetDefaultAudioEndpoint(DataFlow.Render, Role.Multimedia);
            deviceName = device.FriendlyName; deviceStale = false;
        }
        return device;
    }
    private string deviceName = "";
    private sealed class DeviceWatcher(Action changed) : IMMNotificationClient
    {
        public void OnDeviceStateChanged(string deviceId, DeviceState newState) => changed();
        public void OnDeviceAdded(string pwstrDeviceId) => changed();
        public void OnDeviceRemoved(string deviceId) => changed();
        public void OnDefaultDeviceChanged(DataFlow flow, Role role, string defaultDeviceId) => changed();
        public void OnPropertyValueChanged(string pwstrDeviceId, PropertyKey key) { }
    }
    private WasapiLoopbackCapture? capture;
    private float level;
    public float Level => level;
    public bool ReactiveEnabled => capture != null;
    public string? Error { get; private set; }
    public AudioSnapshot Read(bool apps = false)
    {
        try
        {
            var device = Device();
            var list = new List<AppVolume>();
            if (apps)
            {
                var sessions = device.AudioSessionManager.Sessions;
                for (int i = 0; i < sessions.Count; i++)
                {
                    using var session = sessions[i];
                    var pid = (int)session.GetProcessID;
                    if (session.State == AudioSessionState.AudioSessionStateExpired) continue;
                    var name = session.IsSystemSoundsSession ? "Системні звуки" : ProcessName(pid);
                    list.Add(new(pid, name, session.SimpleAudioVolume.Volume, session.SimpleAudioVolume.Mute));
                }
            }
            Error = null;
            return new(true, deviceName, device.AudioEndpointVolume.MasterVolumeLevelScalar, device.AudioEndpointVolume.Mute, list.ToArray());
        }
        catch (Exception e) { deviceStale = true; Error = "Аудіовихід недоступний"; Log.Error("audio read", e); return new(false, "Аудіовихід недоступний", 0, false, []); }
    }
    public bool SetVolume(double value, int? pid = null)
    {
        try
        {
            using var device = enumerator.GetDefaultAudioEndpoint(DataFlow.Render, Role.Multimedia);
            float volume = (float)IslandModel.Clamp(value, 0, 1);
            if (pid == null) { device.AudioEndpointVolume.MasterVolumeLevelScalar = volume; return true; }
            var sessions = device.AudioSessionManager.Sessions; bool found = false;
            for (int i = 0; i < sessions.Count; i++) { using var s = sessions[i]; if (s.GetProcessID == pid) { s.SimpleAudioVolume.Volume = volume; found = true; } }
            return found;
        }
        catch (Exception e) { Log.Error("audio volume", e); return false; }
    }
    public bool SetMute(bool muted, int? pid = null)
    {
        try
        {
            using var device = enumerator.GetDefaultAudioEndpoint(DataFlow.Render, Role.Multimedia);
            if (pid == null) { device.AudioEndpointVolume.Mute = muted; return true; }
            var sessions = device.AudioSessionManager.Sessions; bool found = false;
            for (int i = 0; i < sessions.Count; i++) { using var s = sessions[i]; if (s.GetProcessID == pid) { s.SimpleAudioVolume.Mute = muted; found = true; } }
            return found;
        }
        catch (Exception e) { Log.Error("audio mute", e); return false; }
    }
    public void Reactive(bool enabled)
    {
        capture?.StopRecording(); capture?.Dispose(); capture = null; level = 0;
        if (!enabled) return;
        try
        {
            capture = new WasapiLoopbackCapture();
            capture.DataAvailable += (_, e) =>
            {
                var format = capture?.WaveFormat;
                if (format == null || e.BytesRecorded == 0) return;
                double sum = 0; int n = 0;
                if (format.BitsPerSample == 32)
                    for (int i = 0; i + 3 < e.BytesRecorded; i += format.BlockAlign) { float f = BitConverter.ToSingle(e.Buffer, i); if (float.IsFinite(f)) { sum += f * f; n++; } }
                else if (format.BitsPerSample == 16)
                    for (int i = 0; i + 1 < e.BytesRecorded; i += format.BlockAlign) { double f = BitConverter.ToInt16(e.Buffer, i) / 32768.0; sum += f * f; n++; }
                level = n > 0 ? (float)Math.Clamp(Math.Sqrt(sum / n) * 7, 0, 1) : 0;
            };
            capture.StartRecording();
        }
        catch (Exception e) { Error = "Реакція на звук недоступна"; Log.Error("loopback", e); capture?.Dispose(); capture = null; }
    }
    private static string ProcessName(int pid) { try { using var p = Process.GetProcessById(pid); return p.ProcessName; } catch { return "Програма"; } }
    public void Dispose() { Reactive(false); if (watcher != null) try { enumerator.UnregisterEndpointNotificationCallback(watcher); } catch { } device?.Dispose(); enumerator.Dispose(); }
}
