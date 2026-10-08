using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows.Threading;
using Windows.Media;
using Windows.Media.Core;
using Windows.Media.Playback;
using Windows.Storage;

namespace Island.Windows;

// A real, silent Windows MediaPlayer session used to verify cross-process controls.
// Never included in the normal startup path.
public sealed class Fixture(string output) : IDisposable
{
    private readonly MediaPlayer player = new();
    private readonly DispatcherTimer timer = new() { Interval = TimeSpan.FromMilliseconds(250) };
    private SystemMediaTransportControls? controls;
    private int track = 1;
    private string? wave;
    private string? artwork;
    [DllImport("shell32.dll", CharSet = CharSet.Unicode)] private static extern int SetCurrentProcessExplicitAppUserModelID(string id);
    public async Task Start()
    {
        SetCurrentProcessExplicitAppUserModelID("IslandDesktop.NativeFixture");
        wave = Path.Combine(Path.GetDirectoryName(output)!, "fixture-silent.wav");
        using (var stream = new BinaryWriter(File.Create(wave)))
        {
            const int rate = 8000, seconds = 180, size = rate * seconds * 2;
            stream.Write(System.Text.Encoding.ASCII.GetBytes("RIFF")); stream.Write(size + 36); stream.Write(System.Text.Encoding.ASCII.GetBytes("WAVEfmt "));
            stream.Write(16); stream.Write((short)1); stream.Write((short)1); stream.Write(rate); stream.Write(rate * 2); stream.Write((short)2); stream.Write((short)16);
            stream.Write(System.Text.Encoding.ASCII.GetBytes("data")); stream.Write(size); stream.Write(new byte[size]);
        }
        player.CommandManager.IsEnabled = false;
        player.Source = MediaSource.CreateFromStorageFile(await StorageFile.GetFileFromPathAsync(wave));
        controls = player.SystemMediaTransportControls;
        artwork = Path.Combine(Path.GetDirectoryName(output)!, "fixture-art.png");
        var visual = new System.Windows.Media.DrawingVisual();
        using (var drawing = visual.RenderOpen())
        {
            var gradient = new System.Windows.Media.LinearGradientBrush(System.Windows.Media.Color.FromRgb(88, 174, 201), System.Windows.Media.Color.FromRgb(119, 73, 145), 45);
            drawing.DrawRectangle(gradient, null, new System.Windows.Rect(0, 0, 128, 128));
            var pen = new System.Windows.Media.Pen(System.Windows.Media.Brushes.White, 8);
            drawing.DrawEllipse(null, pen, new System.Windows.Point(64, 64), 30, 30);
            drawing.DrawEllipse(System.Windows.Media.Brushes.White, null, new System.Windows.Point(64, 64), 5, 5);
        }
        var bitmap = new System.Windows.Media.Imaging.RenderTargetBitmap(128, 128, 96, 96, System.Windows.Media.PixelFormats.Pbgra32); bitmap.Render(visual);
        var png = new System.Windows.Media.Imaging.PngBitmapEncoder(); png.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
        using (var file = File.Create(artwork)) png.Save(file);
        controls.DisplayUpdater.Thumbnail = global::Windows.Storage.Streams.RandomAccessStreamReference.CreateFromFile(await StorageFile.GetFileFromPathAsync(artwork));
        controls.IsEnabled = true; controls.IsPlayEnabled = controls.IsPauseEnabled = controls.IsNextEnabled = controls.IsPreviousEnabled = true;
        controls.ButtonPressed += (_, args) => System.Windows.Application.Current.Dispatcher.InvokeAsync(() =>
        {
            switch (args.Button)
            {
                case SystemMediaTransportControlsButton.Play: player.Play(); break;
                case SystemMediaTransportControlsButton.Pause: player.Pause(); break;
                case SystemMediaTransportControlsButton.Next: track++; player.PlaybackSession.Position = TimeSpan.Zero; UpdateMetadata(); break;
                case SystemMediaTransportControlsButton.Previous: track = Math.Max(1, track - 1); player.PlaybackSession.Position = TimeSpan.Zero; UpdateMetadata(); break;
            }
        });
        controls.PlaybackPositionChangeRequested += (_, args) => System.Windows.Application.Current.Dispatcher.InvokeAsync(() => player.PlaybackSession.Position = args.RequestedPlaybackPosition);
        player.PlaybackSession.PlaybackStateChanged += (_, _) => System.Windows.Application.Current.Dispatcher.InvokeAsync(Publish);
        UpdateMetadata(); player.Play(); timer.Tick += (_, _) => Publish(); timer.Start();
    }
    private void UpdateMetadata()
    {
        if (controls == null) return;
        controls.DisplayUpdater.Type = MediaPlaybackType.Music;
        controls.DisplayUpdater.MusicProperties.Title = $"Island Windows · test {track}";
        controls.DisplayUpdater.MusicProperties.Artist = "Local native media fixture";
        controls.DisplayUpdater.MusicProperties.AlbumTitle = "Windows port verification";
        controls.DisplayUpdater.Update();
    }
    private void Publish()
    {
        if (controls == null) return;
        var state = player.PlaybackSession.PlaybackState;
        controls.PlaybackStatus = state == MediaPlaybackState.Playing ? MediaPlaybackStatus.Playing : state == MediaPlaybackState.Paused ? MediaPlaybackStatus.Paused : MediaPlaybackStatus.Stopped;
        controls.UpdateTimelineProperties(new SystemMediaTransportControlsTimelineProperties { StartTime = TimeSpan.Zero, EndTime = TimeSpan.FromSeconds(180), MinSeekTime = TimeSpan.Zero, MaxSeekTime = TimeSpan.FromSeconds(180), Position = player.PlaybackSession.Position });
        File.WriteAllText(output + ".tmp", JsonSerializer.Serialize(new { pid = Environment.ProcessId, track, state = state.ToString(), position = player.PlaybackSession.Position.TotalSeconds }));
        File.Move(output + ".tmp", output, true);
    }
    public void Dispose() { timer.Stop(); player.Dispose(); if (wave != null && File.Exists(wave)) File.Delete(wave); }
}
