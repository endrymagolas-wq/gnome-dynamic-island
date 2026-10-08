using System;
using System.IO;
using System.IO.Pipes;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;

namespace Island.Windows;

public partial class App : System.Windows.Application
{
    private Mutex? mutex;
    private CancellationTokenSource? stop;
    private Fixture? fixture;
    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        DispatcherUnhandledException += (_, args) => { Log.Error("UI", args.Exception); args.Handled = true; };
        if (e.Args.Length > 0 && e.Args[0] == "--edge-fixture")
        {
            var test = new Window { Title="Island Edge Test", WindowState=WindowState.Maximized, Background=System.Windows.Media.Brushes.LightGray, Content=new System.Windows.Controls.TextBlock { Text="Island Desktop · перевірка верхнього краю", Foreground=System.Windows.Media.Brushes.Black, HorizontalAlignment=HorizontalAlignment.Center, VerticalAlignment=VerticalAlignment.Center, FontSize=24 } };
            test.Closed += (_,_)=>Shutdown(); MainWindow=test; test.Show(); return;
        }
        if (e.Args.Length >= 2 && e.Args[0] == "--self-test")
        {
            try { File.WriteAllText(e.Args[1], JsonSerializer.Serialize(SelfTests.Run(), new JsonSerializerOptions { WriteIndented = true })); Shutdown(0); }
            catch (Exception error) { File.WriteAllText(e.Args[1], error.ToString()); Shutdown(1); }
            return;
        }
        if (e.Args.Length >= 2 && e.Args[0] == "--dock-test")
        {
            try { var result=DockTests.Run(out bool success);File.WriteAllText(e.Args[1], JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true })); Shutdown(success?0:1); }
            catch (Exception error) { File.WriteAllText(e.Args[1], error.ToString()); Shutdown(1); }
            return;
        }
        if (e.Args.Length >= 2 && e.Args[0] == "--shell-probe")
        {
            File.WriteAllText(e.Args[1],JsonSerializer.Serialize(NativeTrayPopup.TaskbarAppearance()));Shutdown(0);return;
        }
        if (e.Args.Length >= 2 && e.Args[0] == "--fixture")
        {
            fixture = new Fixture(e.Args[1]);
            try { await fixture.Start(); } catch (Exception error) { File.WriteAllText(e.Args[1], error.ToString()); Shutdown(1); }
            return;
        }
        mutex = new Mutex(true, @"Local\IslandDesktopWindows", out bool fresh);
        if (!fresh) { Shutdown(); return; }
        var window = new MainWindow(); MainWindow = window; window.Show();
        stop = new CancellationTokenSource(); _ = Serve(window, stop.Token);
    }
    private async Task Serve(MainWindow window, CancellationToken cancellation)
    {
        while (!cancellation.IsCancellationRequested)
        {
            try
            {
                using var pipe = new NamedPipeServerStream("IslandDesktopWindows", PipeDirection.InOut, 1, PipeTransmissionMode.Byte, PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
                await pipe.WaitForConnectionAsync(cancellation);
                using var reader = new StreamReader(pipe, leaveOpen: true);
                using var writer = new StreamWriter(pipe, leaveOpen: true) { AutoFlush = true };
                using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellation); timeout.CancelAfter(5000);
                var input = await reader.ReadLineAsync(timeout.Token);
                if (input == null || input.Length > 8192) continue;
                using var request = JsonDocument.Parse(input);
                var operation = request.RootElement.Clone();
                var result = await Dispatcher.InvokeAsync(() => Execute(window, operation));
                await writer.WriteLineAsync(JsonSerializer.Serialize(await result));
            }
            catch (OperationCanceledException) { if (cancellation.IsCancellationRequested) break; }
            catch (Exception error) { Log.Error("local control", error); }
        }
    }
    private async Task<object> Execute(MainWindow w, JsonElement request)
    {
        var command = request.GetProperty("command").GetString();
        switch (command)
        {
            case "airplay-status": return w.AirPlay.State;
            case "airplay-diagnostics": return w.AirPlay.Diagnostics;
            case "airplay": w.ShowAirPlay(); break;
            case "airplay-start": return new { ok = await w.SetAirPlay(true), airplay = w.AirPlay.State };
            case "airplay-stop": return new { ok = await w.SetAirPlay(false), airplay = w.AirPlay.State };
            case "airplay-pin": return new { ok = await w.SetAirPlayPin(request.GetProperty("value").GetBoolean()), airplay = w.AirPlay.State };
            case "airplay-video": return new { ok = await w.SetAirPlayVideo(
                request.TryGetProperty("fullscreen", out var videoFullscreen) ? videoFullscreen.GetBoolean() : null,
                request.TryGetProperty("keepAspect", out var videoAspect) ? videoAspect.GetBoolean() : null,
                request.TryGetProperty("bufferSeconds", out var videoBuffer) ? videoBuffer.GetInt32() : null), airplay = w.AirPlay.State };
            case "nav": if(w.Shell!=null) await w.Shell.InvokeNavigation(request.GetProperty("id").GetString()!); break;
            case "nav-geometry": return w.Shell?.NavigationGeometry() ?? new object();
            case "inspect-ui": w.Shell?.Inspect(true); break;
            case "inspect-off": w.Shell?.Inspect(false); break;
            case "popup-snapshot": w.Shell?.PopupSnapshot(request.GetProperty("path").GetString()!); break;
            case "panel-audit": return w.Shell==null ? new { error="Shell unavailable" } : await w.Shell.AuditTransition();
            case "panel": w.Shell?.Preview(); break;
            case "panel-snapshot": w.Shell?.Snapshot(request.GetProperty("path").GetString()!, false); break;
            case "dock-snapshot": w.Shell?.Snapshot(request.GetProperty("path").GetString()!, true); break;
            case "expand": w.Expand(false); break;
            case "collapse": w.Collapse(); break;
            case "desktop": w.Expand(false); w.ShowDesktop(); break;
            case "settings": w.Expand(false); w.ShowDesktop(); w.ScrollSettings(); break;
            case "snapshot": w.Snapshot(request.GetProperty("path").GetString()!); break;
            case "select": w.Media.Select(request.GetProperty("id").GetString()); await w.Media.Refresh(); break;
            case "playpause": case "play": case "pause": case "next": case "previous": case "seek":
                return new { ok = await w.Media.Command(command, request.TryGetProperty("position", out var position) ? position.GetDouble() : 0) };
            case "volume": return new { ok = w.Audio.SetVolume(request.GetProperty("value").GetDouble(), request.TryGetProperty("pid", out var pid) ? pid.GetInt32() : null) };
            case "mute": return new { ok = w.Audio.SetMute(request.GetProperty("value").GetBoolean(), request.TryGetProperty("pid", out var mutedPid) ? mutedPid.GetInt32() : null) };
            case "reactive": w.Audio.Reactive(request.GetProperty("value").GetBoolean()); break;
            case "focus": w.StartFocus(request.GetProperty("seconds").GetInt32()); break;
            case "focus-stop": w.Settings.FocusUntil = null; w.Settings.Save(); break;
            case "wallpaper": return new { ok = await w.Desktop.WallpaperProperty(request.GetProperty("property").GetString()!, (int)request.GetProperty("value").GetDouble()) };
            case "quit": _ = Dispatcher.InvokeAsync(() => Shutdown()); return new { ok = true };
            case "status": await w.Media.Refresh(); await w.Desktop.RefreshWallpaper(); break;
            default: return new { ok = false, error = "Unknown command" };
        }
        return new { ok = true, pid = Environment.ProcessId, shell = w.Shell?.Status, expanded = w.IsExpanded, visible = w.IsVisible, width = w.ActualWidth, height = w.ActualHeight, left = w.Left, top = w.Top, media = w.Media.State, airplay = w.AirPlay.State, hasArtwork = w.Media.State.Artwork != null, players = w.Media.Choices, playerLabel = w.PlayerLabel, audio = w.Audio.Read(true), wallpaper = w.Desktop.Wallpaper, wallpaperPreferences = w.Desktop.ReadWallpaperPreferences(), focusSeconds = IslandModel.Remaining(w.Settings.FocusUntil, DateTimeOffset.Now).TotalSeconds, audioLevel = w.Audio.Level, reactiveEnabled = w.Audio.ReactiveEnabled };
    }
    protected override void OnExit(ExitEventArgs e)
    {
        stop?.Cancel(); fixture?.Dispose();
        if (MainWindow is MainWindow w) w.Close();
        mutex?.Dispose(); base.OnExit(e);
    }
}
