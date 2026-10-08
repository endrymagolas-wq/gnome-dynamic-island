using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Media.Imaging;

namespace Island.Windows;

public sealed record AirPlaySnapshot(bool Enabled, bool Ready, bool Connected, bool Playing,
    string Name, string Client, string Kind, string Pin, string Status, string? Error, int? Pid, int Port, bool RemoteControl,
    bool VideoWindow, bool VideoFullscreen, bool KeepAspect, int BufferPercent, int BufferSeconds);
public sealed record AirPlayDiagnostic(DateTimeOffset At, string Stage, int? Code = null);

// UxPlay owns the AirPlay protocol and GStreamer playback. This service owns its lifecycle
// and consumes explicit native callbacks; it does not infer songs from diagnostic log text.
public sealed class AirPlayService : IDisposable
{
    public const string SourceId = "island.airplay";
    public const int Port = 7100;
    public const string ReceiverName = "Cortiva Island";
    private readonly Action<Action> dispatch;
    private readonly SemaphoreSlim lifecycle = new(1, 1);
    private readonly SemaphoreSlim controls = new(1, 1);
    private readonly Preferences settings;
    private readonly System.Threading.Timer pulse;
    private readonly HttpClient http = new(new SocketsHttpHandler { UseProxy = false, AllowAutoRedirect = false, ConnectTimeout = TimeSpan.FromSeconds(2) }) { Timeout = TimeSpan.FromSeconds(3) };
    private readonly string package = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, ".."));
    private readonly string data = Path.Combine(Preferences.Data, "airplay");
    private Process? process;
    private ReceiverJob? job;
    private TaskCompletionSource<bool>? startup;
    private DacpEndpoint? remote;
    private string activeRemote = "", dacpId = "", client = "", kind = "", pin = "", title = "", artist = "";
    private string? error;
    private bool enabled, ready, connected, playing, disposed, resolving, requirePin;
    private bool videoWindow, videoFullscreen, keepAspect = true, videoSeek;
    private int bufferPercent = 100, bufferSeconds = 5;
    private double seekStart, seekEnd;
    private DateTimeOffset lastActivity, positionAt, nextResolve, retryAt, pinUntil;
    private double position, duration;
    private int retries;
    private BitmapSource? artwork;
    private readonly List<AirPlayDiagnostic> diagnostics = new();
    public IReadOnlyList<AirPlayDiagnostic> Diagnostics => diagnostics.ToArray();
    public event Action? Changed;

    public AirPlayService(Action<Action> dispatch, Preferences settings)
    {
        this.dispatch = dispatch;
        this.settings = settings;
        pulse = new System.Threading.Timer(_ => Post(Pulse), null, 1000, 1000);
    }
    private void Post(Action action) { if (!disposed) dispatch(() => { if (!disposed) action(); }); }
    public AirPlaySnapshot State => new(enabled, ready, connected, IsPlaying, ReceiverName, client, kind, pin,
        !enabled ? "Вимкнено" : error != null ? "Не вдалося запустити" : !ready ? "Підготовка приймача…" : pin.Length > 0 ? "Введи цей код на своєму пристрої" : connected ?
        (kind == "mirroring" ? "Приймає екран" : kind == "video" && (duration <= 0 || bufferPercent < 100) ? "Завантаження відео…" :
         IsPlaying ? kind == "video" ? "Відтворює відео" : "Приймає звук" : "Підключено · пауза") : "Готовий до підключення",
        error, process is { HasExited: false } p ? p.Id : null, Port, remote != null && activeRemote.Length > 0,
        videoWindow, videoFullscreen, keepAspect, bufferPercent, bufferSeconds);
    private bool IsPlaying => connected && playing && DateTimeOffset.UtcNow - lastActivity < TimeSpan.FromSeconds(3);
    private double PositionNow => Math.Clamp(position + (playing ? Math.Max(0, ((kind == "video" ? DateTimeOffset.UtcNow : DateTimeOffset.UtcNow < lastActivity.AddSeconds(3) ? DateTimeOffset.UtcNow : lastActivity.AddSeconds(3)) - positionAt).TotalSeconds) : 0), 0, Math.Max(0, duration));
    public MediaSnapshot Media => new()
    {
        Available = connected, Playing = IsPlaying, Source = SourceId,
        Title = title.Length > 0 ? title : kind == "mirroring" ? "Екран твого пристрою" : kind == "video" ? "Відео через AirPlay" : "Музика через AirPlay",
        Artist = artist.Length > 0 ? artist : client.Length > 0 ? client : "iPhone · iPad · Mac",
        Artwork = artwork, Start = kind == "video" ? seekStart : 0, End = kind == "video" && videoSeek ? seekEnd : duration, Position = PositionNow,
        CanToggle = connected && (kind == "video" && duration > 0 || kind == "audio" && State.RemoteControl), CanNext = kind == "audio" && State.RemoteControl,
        CanPrevious = kind == "audio" && State.RemoteControl, CanSeek = connected && kind == "video" && videoSeek
    };

    public async Task<bool> SetEnabled(bool value, bool pinRequired = true)
    {
        await lifecycle.WaitAsync();
        try
        {
            if (disposed) return false;
            enabled = value; requirePin = pinRequired;
            if (!value) { await StopChild(); error = null; Changed?.Invoke(); return true; }
            if (process is { HasExited: false }) return ready;
            retries = 0; retryAt = default;
            return await StartChild();
        }
        finally { lifecycle.Release(); }
    }
    public async Task<bool> Restart(bool pinRequired)
    {
        await SetEnabled(false, pinRequired);
        return await SetEnabled(true, pinRequired);
    }
    private async Task<bool> StartChild()
    {
        var binary = Path.Combine(package, "receiver", "bin", "uxplay.exe");
        if (!File.Exists(binary)) { error = "Файли AirPlay-приймача відсутні"; Changed?.Invoke(); return false; }
        try
        {
            Directory.CreateDirectory(data);
            foreach (string name in new[] { "remote.txt", "coverart.bin" })
                try { File.Delete(Path.Combine(data, name)); } catch (IOException) { }
            File.WriteAllText(Path.Combine(data, "receiver.cfg"), "# Managed by Island Desktop\n", new UTF8Encoding(false));
            var identity = Path.Combine(data, "identity.txt");
            if (!File.Exists(identity)) { var bytes = Guid.NewGuid().ToByteArray(); bytes[0] = 2; File.WriteAllText(identity, BitConverter.ToString(bytes, 0, 6).Replace('-', ':')); }
            var mac = File.ReadAllText(identity).Trim();
            if (!Regex.IsMatch(mac, "^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")) throw new InvalidDataException("Receiver identity is invalid");
            var info = new ProcessStartInfo(binary)
            {
                UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = data,
                RedirectStandardOutput = true, RedirectStandardError = true, RedirectStandardInput = true,
                StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
            };
            string videoSink = $"d3d11videosink fullscreen-toggle-mode=6 fullscreen={settings.AirPlayVideoFullscreen.ToString().ToLowerInvariant()} force-aspect-ratio={settings.AirPlayVideoKeepAspect.ToString().ToLowerInvariant()}";
            foreach (string arg in new[] { "-n", ReceiverName, "-nh", "-p", Port.ToString(), "-m", mac, "-s", "1920x1080", "-fps", "30", "-avdec", "-as", "wasapisink", "-vs", videoSink, "-nofreeze", "-hls", "2", "-lang", "uk:en", "-ca", Path.Combine(data, "coverart.bin"), "-dacp", Path.Combine(data, "remote.txt"), "-key", Path.Combine(data, "receiver-key.pem"), "-rc", Path.Combine(data, "receiver.cfg") }) info.ArgumentList.Add(arg);
            // A fixed code: UxPlay's random one is consumed by the first pair-setup attempt, and iOS first
            // retries the code it remembered, so the code the user then types was checked against "0000".
            if (requirePin) { info.ArgumentList.Add("-pin"); info.ArgumentList.Add(ReceiverPin()); info.ArgumentList.Add("-reg"); info.ArgumentList.Add(Path.Combine(data, "paired-devices.txt")); }
            info.Environment["ISLAND_EVENTS"] = "1";
            info.Environment["ISLAND_HLS_AUDIO_SINK"] = "wasapisink";
            info.Environment["ISLAND_HLS_BUFFER_SECONDS"] = Math.Clamp(settings.AirPlayVideoBufferSeconds, 2, 8).ToString(CultureInfo.InvariantCulture);
            info.Environment["PATH"] = Path.Combine(package, "receiver", "bin") + Path.PathSeparator + Environment.GetEnvironmentVariable("PATH");
            info.Environment["GST_PLUGIN_SYSTEM_PATH"] = Path.Combine(package, "receiver", "lib", "gstreamer-1.0");
            info.Environment["GST_PLUGIN_PATH"] = "";
            info.Environment["GST_PLUGIN_SCANNER"] = Path.Combine(package, "receiver", "libexec", "gstreamer-1.0", "gst-plugin-scanner.exe");
            info.Environment["GST_REGISTRY"] = Path.Combine(data, "registry-1.28.bin");
            info.Environment["GSETTINGS_SCHEMA_DIR"] = Path.Combine(package, "receiver", "share", "glib-2.0", "schemas");
            info.Environment["GIO_MODULE_DIR"] = Path.Combine(package, "receiver", "lib", "gio", "modules");
            info.Environment["SSL_CERT_FILE"] = Path.Combine(package, "receiver", "etc", "ssl", "certs", "ca-bundle.crt");
            info.Environment["UXPLAYRC"] = Path.Combine(data, "receiver.cfg");
            ready = false; error = null; ClearSession(); startup = new(TaskCreationOptions.RunContinuationsAsynchronously);
            var child = new Process { StartInfo = info, EnableRaisingEvents = true };
            process = child;
            child.OutputDataReceived += (_, e) => { if (e.Data is { Length: > 8 and < 32768 } line && line.StartsWith("@island ", StringComparison.Ordinal)) Post(() => { if (process == child) Receive(line[8..]); }); };
            // Drain diagnostics without exposing device tokens or retaining source media URLs.
            child.ErrorDataReceived += (_, _) => { };
            child.Exited += (_, _) => Post(() => { if (process == child) ChildExited(child); });
            if (!child.Start()) throw new InvalidOperationException("Receiver process could not start");
            job = new ReceiverJob(child);
            child.BeginOutputReadLine(); child.BeginErrorReadLine(); Changed?.Invoke();
            try { return await startup.Task.WaitAsync(TimeSpan.FromSeconds(12)); }
            catch (TimeoutException) { error = "Приймач не завершив запуск · спробуй увімкнути ще раз"; await StopChild(); Changed?.Invoke(); return false; }
        }
        catch (Exception e)
        {
            Log.Error("AirPlay startup", e); error = "Не вдалося запустити AirPlay-приймач";
            await StopChild(); Changed?.Invoke(); return false;
        }
    }
    private string ReceiverPin()
    {
        var file = Path.Combine(data, "pin.txt");
        try { if (File.ReadAllText(file).Trim() is { Length: 4 } saved && Regex.IsMatch(saved, "^[1-9][0-9]{3}$")) return saved; } catch (IOException) { }
        var code = System.Security.Cryptography.RandomNumberGenerator.GetInt32(1000, 10000).ToString(CultureInfo.InvariantCulture);
        File.WriteAllText(file, code);
        return code;
    }
    private void ChildExited(Process child)
    {
        startup?.TrySetResult(false); ready = false; ClearSession();
        error = $"Приймач завершив роботу (код {child.ExitCode})";
        process = null; job?.Dispose(); job = null; child.Dispose();
        if (enabled && retries < 3) retryAt = DateTimeOffset.UtcNow.AddSeconds(5 * ++retries);
        Changed?.Invoke();
    }
    private async Task StopChild()
    {
        var child = process; process = null; ready = false; startup?.TrySetResult(false); ClearSession();
        if (child != null)
        {
            try
            {
                if (!child.HasExited) { await child.StandardInput.WriteLineAsync("quit"); await child.StandardInput.FlushAsync(); await child.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(2)); }
            }
            catch { try { if (!child.HasExited) { child.Kill(true); await child.WaitForExitAsync(); } } catch { } }
            child.Dispose();
        }
        job?.Dispose(); job = null; retryAt = default;
    }
    private void ClearSession(bool preservePin = false)
    {
        connected = playing = false; client = kind = title = artist = ""; position = duration = 0; artwork = null;
        videoWindow = videoFullscreen = videoSeek = false; seekStart = seekEnd = 0; bufferPercent = 100;
        if (!preservePin) { pin = ""; pinUntil = default; }
        remote = null; activeRemote = dacpId = ""; nextResolve = default;
    }
    private void Receive(string line)
    {
        try
        {
            using var document = JsonDocument.Parse(line); var e = document.RootElement;
            string Text(string key) => e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.String ? (v.GetString() ?? "")[..Math.Min(512, (v.GetString() ?? "").Length)] : "";
            string eventName = Text("event");
            if (eventName == "phase") { RecordDiagnostic(Text("stage")); return; }
            if (eventName == "response") { RecordDiagnostic("response", e.GetProperty("code").GetInt32()); return; }
            if (eventName is "ready" or "pin" or "stream" or "disconnected" or "paused" or "playing" || eventName == "activity" && !playing)
                RecordDiagnostic(eventName);
            switch (eventName)
            {
                case "ready": ready = true; error = null; startup?.TrySetResult(true); break;
                case "client": client = Text("name"); break;
                case "pin": pin = Text("pin"); pinUntil = DateTimeOffset.UtcNow.AddMinutes(2); break;
                case "stream": connected = true; kind = Text("kind"); pin = ""; title = artist = ""; position = duration = 0; artwork = null; break;
                case "activity": connected = true; if (kind.Length == 0 || Text("kind") == "mirroring") kind = Text("kind"); lastActivity = DateTimeOffset.UtcNow; if (!playing) positionAt = lastActivity; playing = true; pin = ""; break;
                // A client's requested rate is not proof that the HLS pipeline
                // is playing. Its main-context telemetry is authoritative.
                case "playing": if (kind == "video" || !connected) return; lastActivity = DateTimeOffset.UtcNow; positionAt = lastActivity; playing = true; break;
                case "paused": position = PositionNow; positionAt = DateTimeOffset.UtcNow; playing = false; break;
                case "video-state":
                    videoWindow = e.GetProperty("window").GetBoolean(); videoFullscreen = e.GetProperty("fullscreen").GetBoolean();
                    keepAspect = e.GetProperty("keepAspect").GetBoolean(); bufferPercent = Math.Clamp(e.GetProperty("buffer").GetInt32(), 0, 100);
                    bufferSeconds = Math.Clamp(e.GetProperty("bufferSeconds").GetInt32(), 2, 8);
                    if (e.GetProperty("hls").GetBoolean() && connected && kind == "video")
                    {
                        duration = IslandModel.Clamp(e.GetProperty("duration").GetDouble(), 0, 86400);
                        position = IslandModel.Clamp(e.GetProperty("position").GetDouble(), 0, duration);
                        seekStart = IslandModel.Clamp(e.GetProperty("seekStart").GetDouble(), 0, duration);
                        seekEnd = IslandModel.Clamp(seekStart + e.GetProperty("seekDuration").GetDouble(), seekStart, duration);
                        videoSeek = seekEnd > seekStart;
                        lastActivity = positionAt = DateTimeOffset.UtcNow; playing = e.GetProperty("playing").GetBoolean();
                    }
                    break;
                case "video-stopped": ClearSession(); break;
                case "metadata": title = Text("title"); artist = Text("artist"); break;
                case "artwork": ReadArtwork(); break;
                case "progress":
                    var timeline = Timeline(e.GetProperty("start").GetUInt32(), e.GetProperty("current").GetUInt32(), e.GetProperty("end").GetUInt32());
                    position = timeline.Position; duration = timeline.Duration; positionAt = DateTimeOffset.UtcNow; break;
                // PIN negotiation can close its initial HTTP connection before the user
                // types the code. This is not cancellation of the pairing request.
                case "disconnected": ClearSession(preservePin: pin.Length > 0); break;
                default: return;
            }
            Changed?.Invoke();
        }
        catch (Exception e) when (e is JsonException or InvalidOperationException or OverflowException) { /* Discard malformed telemetry; keep the receiver alive. */ }
    }
    private void RecordDiagnostic(string stage, int? code = null)
    {
        // The native bridge supplies fixed stage names and numeric response codes only.
        // Keep no headers, PIN values, device identifiers, media URLs or authorization tokens.
        if (!Regex.IsMatch(stage, "^[a-z][a-z0-9-]{0,47}$")) return;
        var now = DateTimeOffset.UtcNow;
        if (diagnostics.Count > 0 && diagnostics[^1] is var last && last.Stage == stage && last.Code == code &&
            (stage == "response" && code == 200 || now - last.At < TimeSpan.FromMilliseconds(250))) return;
        diagnostics.Add(new(now, stage, code));
        if (diagnostics.Count > 128) diagnostics.RemoveAt(0);
    }
    public static (double Position, double Duration) Timeline(uint start, uint current, uint end)
    {
        double length = unchecked(end - start) / 44100.0;
        return length is > 0 and <= 86400 ? (Math.Clamp(unchecked(current - start) / 44100.0, 0, length), length) : (0, 0);
    }
    private void ReadArtwork()
    {
        try
        {
            using var input = new FileStream(Path.Combine(data, "coverart.bin"), FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            if (input.Length is <= 0 or > 4 * 1024 * 1024) return;
            var image = new BitmapImage(); image.BeginInit(); image.CacheOption = BitmapCacheOption.OnLoad; image.DecodePixelWidth = 256; image.StreamSource = input; image.EndInit(); image.Freeze(); artwork = image;
        }
        catch (Exception e) when (e is IOException or NotSupportedException or System.IO.FileFormatException or ArgumentException) { }
    }
    private void Pulse()
    {
        if (pin.Length > 0 && DateTimeOffset.UtcNow >= pinUntil) { pin = ""; Changed?.Invoke(); }
        if (playing && !IsPlaying) { position = PositionNow; playing = false; positionAt = DateTimeOffset.UtcNow; Changed?.Invoke(); }
        if (ready && connected && !resolving && DateTimeOffset.UtcNow >= nextResolve) _ = ResolveRemote();
        if (enabled && process == null && retryAt != default && DateTimeOffset.UtcNow >= retryAt)
        {
            retryAt = default;
            _ = RestartAfterFailure();
        }
    }
    private async Task RestartAfterFailure()
    {
        await lifecycle.WaitAsync();
        try { if (enabled && !disposed && process == null) await StartChild(); }
        finally { lifecycle.Release(); }
    }
    private async Task ResolveRemote()
    {
        resolving = true; nextResolve = DateTimeOffset.UtcNow.AddSeconds(10);
        var owner = process;
        try
        {
            string[] lines = await File.ReadAllLinesAsync(Path.Combine(data, "remote.txt"));
            if (lines.Length != 2 || !Regex.IsMatch(lines[0], "^[0-9A-Fa-f]{1,16}$") || !Regex.IsMatch(lines[1], "^[0-9]{1,20}$")) return;
            string id = lines[0], token = lines[1];
            if (id != dacpId || token != activeRemote) remote = null;
            var endpoint = await DacpDiscovery.Find(id);
            if (!disposed && process == owner && connected)
            {
                remote = endpoint; activeRemote = token; dacpId = id; Changed?.Invoke();
            }
        }
        catch (Exception e) when (e is IOException or System.Net.Sockets.SocketException or OperationCanceledException) { remote = null; }
        finally { resolving = false; }
    }
    public async Task<bool> Command(string command, double targetPosition = 0)
    {
        if (connected && kind == "video")
        {
            string? native = command switch
            {
                "play" when duration > 0 => "media-play", "pause" when duration > 0 => "media-pause",
                "playpause" when duration > 0 => IsPlaying ? "media-pause" : "media-play",
                "seek" when videoSeek && double.IsFinite(targetPosition) => "media-seek " + Math.Clamp(targetPosition, seekStart, seekEnd).ToString("F3", CultureInfo.InvariantCulture),
                _ => null
            };
            return native != null && await SendNative(native);
        }
        string? action = command switch { "playpause" => "playpause", "pause" => "pause", "play" => "play", "next" => "nextitem", "previous" => "previtem", _ => null };
        if (action == null || !connected || kind != "audio" || remote == null || activeRemote.Length == 0) return false;
        try
        {
            var target = remote;
            using var request = new HttpRequestMessage(HttpMethod.Get, $"http://{target.Address}:{target.Port}/ctrl-int/1/{action}");
            request.Headers.Add("Active-Remote", activeRemote);
            using var response = await http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead);
            if (!response.IsSuccessStatusCode) { remote = null; Changed?.Invoke(); return false; }
            // The native activity/flush callbacks provide authoritative playback state.
            return true;
        }
        catch (Exception e) when (e is HttpRequestException or OperationCanceledException) { remote = null; Changed?.Invoke(); return false; }
    }
    private async Task<bool> SendNative(string command)
    {
        await controls.WaitAsync();
        try
        {
            if (disposed || process is not { HasExited: false } child) return false;
            await child.StandardInput.WriteLineAsync(command); await child.StandardInput.FlushAsync(); return true;
        }
        catch (Exception e) when (e is IOException or InvalidOperationException or ObjectDisposedException) { return false; }
        finally { controls.Release(); }
    }
    public async Task<bool> ApplyVideoOptions()
    {
        bool window = await SendNative($"video-window {(settings.AirPlayVideoFullscreen ? 1 : 0)} {(settings.AirPlayVideoKeepAspect ? 1 : 0)}");
        bool buffer = await SendNative("video-buffer " + Math.Clamp(settings.AirPlayVideoBufferSeconds, 2, 8).ToString(CultureInfo.InvariantCulture));
        return window && buffer;
    }
    public void Dispose()
    {
        if (disposed) return; enabled = false; disposed = true; pulse.Dispose();
        var child = process; process = null;
        if (child != null)
        {
            try { if (!child.HasExited) { child.StandardInput.WriteLine("quit"); child.StandardInput.Flush(); if (!child.WaitForExit(1500)) child.Kill(true); } } catch { }
            child.Dispose();
        }
        job?.Dispose(); http.Dispose();
    }
}
