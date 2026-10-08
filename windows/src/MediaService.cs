using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Media.Imaging;
using Windows.Media.Control;

namespace Island.Windows;

public record SessionChoice(string Id, string Name);
public sealed class MediaSnapshot
{
    public bool Available { get; set; }
    public bool Playing { get; set; }
    public bool CanToggle { get; set; }
    public bool CanNext { get; set; }
    public bool CanPrevious { get; set; }
    public bool CanSeek { get; set; }
    public string Source { get; set; } = "";
    public string Title { get; set; } = "Увімкни музику або відео";
    public string Artist { get; set; } = "Плеєр з’явиться тут автоматично";
    public double Position { get; set; }
    public double Start { get; set; }
    public double End { get; set; }
    [System.Text.Json.Serialization.JsonIgnore] public BitmapSource? Artwork { get; set; }
}

public sealed class MediaService : IDisposable
{
    private GlobalSystemMediaTransportControlsSessionManager? manager;
    private GlobalSystemMediaTransportControlsSession? session;
    private bool dirty = true, reading, disposed;
    private string? selection;
    private AirPlayService? airplay;
    public string? Error { get; private set; }
    public MediaSnapshot State { get; private set; } = new();
    public IReadOnlyList<SessionChoice> Choices { get; private set; } = [];
    public event Action? Changed;

    public void AttachAirPlay(AirPlayService service) => airplay = service;

    public async Task Initialize()
    {
        try
        {
            manager = await GlobalSystemMediaTransportControlsSessionManager.RequestAsync();
            manager.SessionsChanged += ManagerChanged;
            manager.CurrentSessionChanged += CurrentChanged;
            await Refresh();
        }
        catch (Exception e) { Error = "Windows не надав доступ до медіасесій"; Log.Error("media initialization", e); }
    }
    private void ManagerChanged(GlobalSystemMediaTransportControlsSessionManager sender, SessionsChangedEventArgs args) => dirty = true;
    private void CurrentChanged(GlobalSystemMediaTransportControlsSessionManager sender, CurrentSessionChangedEventArgs args) => dirty = true;
    private void PropertiesChanged(GlobalSystemMediaTransportControlsSession sender, MediaPropertiesChangedEventArgs args) => dirty = true;
    private void PlaybackChanged(GlobalSystemMediaTransportControlsSession sender, PlaybackInfoChangedEventArgs args) => dirty = true;
    private void TimelineChanged(GlobalSystemMediaTransportControlsSession sender, TimelinePropertiesChangedEventArgs args) => dirty = true;

    public void Select(string? id) { selection = string.IsNullOrEmpty(id) ? null : id; dirty = true; }
    public async Task Refresh()
    {
        if (disposed || reading) return;
        reading = true;
        try
        {
            var sessions = manager?.GetSessions().ToArray() ?? [];
            var choices = sessions.Select(s => new SessionChoice(s.SourceAppUserModelId, Friendly(s.SourceAppUserModelId))).DistinctBy(s => s.Id);
            var incoming = airplay?.Media;
            bool receiving = incoming?.Available == true;
            Choices = receiving ? choices.Append(new SessionChoice(AirPlayService.SourceId, "AirPlay · " + (airplay!.State.Client.Length > 0 ? airplay.State.Client : "твій пристрій"))).ToArray() : choices.ToArray();
            if (receiving && (selection == AirPlayService.SourceId || selection == null && (incoming!.Playing || State.Source == AirPlayService.SourceId || sessions.Length == 0)))
            {
                Unsubscribe(); session = null; dirty = true; State = incoming!; Error = null; Changed?.Invoke(); return;
            }
            var next = selection == null ? manager?.GetCurrentSession() : sessions.FirstOrDefault(s => s.SourceAppUserModelId == selection);
            if (next == null) { selection = null; next = manager?.GetCurrentSession() ?? sessions.FirstOrDefault(); }
            if (session != next)
            {
                Unsubscribe(); session = next; dirty = true; State = new();
                if (session != null) { session.MediaPropertiesChanged += PropertiesChanged; session.PlaybackInfoChanged += PlaybackChanged; session.TimelinePropertiesChanged += TimelineChanged; }
            }
            if (session == null) { State = new(); Changed?.Invoke(); return; }
            var current = session;
            var info = current.GetPlaybackInfo(); var timeline = current.GetTimelineProperties();
            // Windows may retire a session between enumeration and the snapshot calls.
            if (info == null || timeline == null || info.Controls == null)
            {
                State = new(); dirty = true; Changed?.Invoke(); return;
            }
            if (dirty)
            {
                dirty = false;
                var properties = await current.TryGetMediaPropertiesAsync();
                if (disposed || properties == null) return;
                var artwork = await ReadArtwork(properties.Thumbnail);
                State.Title = string.IsNullOrWhiteSpace(properties.Title) ? Friendly(current.SourceAppUserModelId) : properties.Title;
                State.Artist = string.IsNullOrWhiteSpace(properties.Artist) ? Friendly(current.SourceAppUserModelId) : properties.Artist;
                State.Artwork = artwork;
            }
            State.Available = true; State.Source = current.SourceAppUserModelId;
            State.Playing = info.PlaybackStatus == GlobalSystemMediaTransportControlsSessionPlaybackStatus.Playing;
            State.CanToggle = info.Controls.IsPlayPauseToggleEnabled || (State.Playing ? info.Controls.IsPauseEnabled : info.Controls.IsPlayEnabled);
            State.CanNext = info.Controls.IsNextEnabled; State.CanPrevious = info.Controls.IsPreviousEnabled; State.CanSeek = info.Controls.IsPlaybackPositionEnabled;
            State.Start = timeline.StartTime.TotalSeconds; State.End = timeline.EndTime.TotalSeconds;
            var delta = State.Playing ? Math.Max(0, (DateTimeOffset.UtcNow - timeline.LastUpdatedTime).TotalSeconds) : 0;
            State.Position = Math.Clamp(timeline.Position.TotalSeconds + delta, State.Start, Math.Max(State.Start, State.End));
            Error = null; Changed?.Invoke();
        }
        catch (System.Runtime.InteropServices.COMException e) when (unchecked((uint)e.HResult) is 0x800706BA or 0x80010108 or 0x80000013)
        {
            Unsubscribe(); session = null; dirty = true; State = new(); Changed?.Invoke();
        }
        catch (Exception e) { dirty = true; Error = "Плеєр тимчасово недоступний"; State = new(); Changed?.Invoke(); Log.Error("media refresh", e); }
        finally { reading = false; }
    }
    public async Task<bool> Command(string command, double position = 0)
    {
        if (State.Source == AirPlayService.SourceId && airplay != null)
        {
            bool handled = await airplay.Command(command, position); await Refresh(); return handled;
        }
        var current = session;
        if (current == null) return false;
        try
        {
            bool result = command switch
            {
                "playpause" => await current.TryTogglePlayPauseAsync(),
                "play" => await current.TryPlayAsync(),
                "pause" => await current.TryPauseAsync(),
                "next" => await current.TrySkipNextAsync(),
                "previous" => await current.TrySkipPreviousAsync(),
                "seek" when State.CanSeek => await current.TryChangePlaybackPositionAsync(TimeSpan.FromSeconds(Math.Clamp(position, State.Start, State.End)).Ticks),
                _ => false
            };
            dirty = true; await Refresh(); return result;
        }
        catch (Exception e) { Log.Error("media command", e); return false; }
    }
    private static async Task<BitmapSource?> ReadArtwork(global::Windows.Storage.Streams.IRandomAccessStreamReference? reference)
    {
        if (reference == null) return null;
        try
        {
            using var stream = await reference.OpenReadAsync();
            if (stream.Size > 4 * 1024 * 1024) return null;
            using var input = stream.AsStreamForRead();
            var image = new BitmapImage(); image.BeginInit(); image.CacheOption = BitmapCacheOption.OnLoad; image.DecodePixelWidth = 256; image.StreamSource = input; image.EndInit(); image.Freeze(); return image;
        }
        catch { return null; }
    }
    public static string Friendly(string id)
    {
        if (id == AirPlayService.SourceId) return "AirPlay";
        if (id.Contains("spotify", StringComparison.OrdinalIgnoreCase)) return "Spotify";
        if (id.Contains("chrome", StringComparison.OrdinalIgnoreCase)) return "Chrome";
        if (id.Contains("msedge", StringComparison.OrdinalIgnoreCase)) return "Edge";
        if (id.Contains("firefox", StringComparison.OrdinalIgnoreCase)) return "Firefox";
        if (id.Contains("vlc", StringComparison.OrdinalIgnoreCase)) return "VLC";
        return Path.GetFileNameWithoutExtension(id.Split('!').Last());
    }
    private void Unsubscribe()
    {
        if (session == null) return;
        session.MediaPropertiesChanged -= PropertiesChanged; session.PlaybackInfoChanged -= PlaybackChanged; session.TimelinePropertiesChanged -= TimelineChanged;
    }
    public void Dispose()
    {
        disposed = true; Unsubscribe();
        if (manager != null) { manager.SessionsChanged -= ManagerChanged; manager.CurrentSessionChanged -= CurrentChanged; }
    }
}
