using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Microsoft.Win32;
using Forms = System.Windows.Forms;

namespace Island.Windows;

public partial class MainWindow : Window
{
    public readonly Preferences Settings = Preferences.Load();
    public readonly MediaService Media = new();
    public readonly AudioService Audio = new();
    public readonly DesktopService Desktop = new();
    public readonly AirPlayService AirPlay;
    public bool IsExpanded { get; private set; }
    public DesktopShell? Shell { get; private set; }
    private bool initialized, updating, seeking, tickBusy, locked;
    public enum IslandView { Home, Control, Scene, AirPlay, Settings, Pairing }
    private IslandView view = IslandView.Home;
    private IntPtr handle;
    private double center;
    private string? choicesKey;
    public string PlayerLabel => (PlayerChoice.SelectedItem as SessionChoice)?.Name ?? "";
    private readonly DispatcherTimer timer = new() { Interval = TimeSpan.FromSeconds(1) };
    private readonly DispatcherTimer waveTimer = new() { Interval = TimeSpan.FromMilliseconds(90) };
    private readonly DispatcherTimer hoverTimer = new() { Interval = TimeSpan.FromMilliseconds(500) };
    private readonly DispatcherTimer leaveTimer = new() { Interval = TimeSpan.FromSeconds(2) };
    private Forms.NotifyIcon? tray;
    private EcoMode? eco;
    private DateTimeOffset nextWallpaper;

    public MainWindow()
    {
        InitializeComponent();
        AirPlay = new(action => Dispatcher.BeginInvoke(action), Settings); Media.AttachAirPlay(AirPlay);
        Previous.Content = MakeIcon("\uE892", 20); Next.Content = MakeIcon("\uE893", 20); Mute.Content = MakeIcon("\uE767", 16);
        PlayPause.Content = MakeIcon("\uE768", 22); ((TextBlock)PlayPause.Content).Foreground = Brushes.Black;
        Volumetric(Volume); ApplyMorph(); SelectTab();
        Loaded += async (_, _) => await Initialize();
        SourceInitialized += (_, _) => { handle = new WindowInteropHelper(this).Handle; DesktopService.NoActivate(handle); Position(); };
        Deactivated += (_, _) => { if (IsExpanded) Collapse(); };
        PreviewKeyDown += (_, e) => { if (e.Key == Key.Escape) { Collapse(); e.Handled = true; } };
        MouseEnter += (_, _) => leaveTimer.Stop();
        MouseLeave += (_, _) => { if (IsExpanded && Settings.HoverExpand) leaveTimer.Start(); };
        hoverTimer.Tick += (_, _) => { hoverTimer.Stop(); if (IsMouseOver && Settings.HoverExpand && !locked) Shell?.Preview(); };
        leaveTimer.Tick += (_, _) => { leaveTimer.Stop(); if (!IsMouseOver) Collapse(); };
        timer.Tick += async (_, _) => await Tick();
        waveTimer.Tick += (_, _) => { Wave.Playing = Media.State.Playing; Wave.Animate = Settings.Animations; Wave.Reactive = Settings.AudioReactive; Wave.Level = Audio.Level; if (IsVisible && !IsExpanded && (Media.State.Playing || Settings.AudioReactive)) Wave.InvalidateVisual(); };
        SystemEvents.SessionSwitch += SessionSwitch;
        SystemEvents.DisplaySettingsChanged += DisplayChanged;
        var menu = new ContextMenu();
        AddMenu(menu, "Відкрити острівець", () => Expand());
        AddMenu(menu, "Керування ПК", () => { Expand(); ShowDesktop(); });
        AddMenu(menu, "Фокус · 25 хв", () => StartFocus(25 * 60));
        AddMenu(menu, "Lively Wallpaper", DesktopService.OpenLively);
        menu.Items.Add(new Separator());
        AddMenu(menu, "Закрити", () => System.Windows.Application.Current.Shutdown());
        ContextMenu = menu;
        Closed += (_, _) => Cleanup();
    }
    private static void AddMenu(ContextMenu menu, string title, Action action) { var item = new MenuItem { Header = title }; item.Click += (_, _) => action(); menu.Items.Add(item); }
    private static TextBlock MakeIcon(string glyph, double size) => new() { Text = glyph, FontFamily = new FontFamily("Segoe Fluent Icons, Segoe MDL2 Assets"), FontSize = size, VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center };
    /// <summary>
    /// Control Center slab behaviour: press swells the slab, dragging moves the fill relative to where you grabbed it,
    /// dragging past either end rubber-bands the slab in that direction, and release springs it back. A tap without
    /// movement glides the fill to the tapped point.
    /// </summary>
    private void Volumetric(Slider slider)
    {
        bool vertical = slider.Orientation == Orientation.Vertical;
        var stretch = new ScaleTransform(); slider.RenderTransform = stretch; slider.RenderTransformOrigin = new Point(.5, .5);
        Point grab = default; double grabValue = 0; bool moved = false;
        double Length() => Math.Max(1, vertical ? slider.ActualHeight : slider.ActualWidth);
        double Range() => slider.Maximum - slider.Minimum;
        // Increasing direction is up for vertical slabs and right for horizontal ones.
        double Travel(Point p) => vertical ? grab.Y - p.Y : p.X - grab.X;
        double ValueAt(Point p) { double t = vertical ? 1 - p.Y / Length() : p.X / Length(); return slider.Minimum + Math.Clamp(t, 0, 1) * Range(); }
        void Clip()
        {
            slider.ApplyTemplate();
            if (slider.Template?.FindName("Body", slider) is FrameworkElement body && body.ActualWidth > 0)
                body.Clip = IslandModel.Squircle(body.ActualWidth, body.ActualHeight, Math.Min(18, Math.Min(body.ActualWidth, body.ActualHeight) * .34));
        }
        void Scale(double along, double across, bool spring)
        {
            double alongX = vertical ? across : along, alongY = vertical ? along : across;
            if (!spring || !Settings.Animations)
            {
                stretch.BeginAnimation(ScaleTransform.ScaleXProperty, null); stretch.BeginAnimation(ScaleTransform.ScaleYProperty, null);
                stretch.ScaleX = alongX; stretch.ScaleY = alongY; return;
            }
            var ease = new SpringEase { Damping = .5 };
            stretch.BeginAnimation(ScaleTransform.ScaleXProperty, new DoubleAnimation(alongX, TimeSpan.FromMilliseconds(520)) { EasingFunction = ease });
            stretch.BeginAnimation(ScaleTransform.ScaleYProperty, new DoubleAnimation(alongY, TimeSpan.FromMilliseconds(520)) { EasingFunction = ease });
        }
        void Glide(double to)
        {
            double from = slider.Value;
            slider.BeginAnimation(Slider.ValueProperty, null);
            if (!Settings.Animations) { slider.Value = to; return; }
            slider.Value = to;
            slider.BeginAnimation(Slider.ValueProperty, new DoubleAnimation(from, to, TimeSpan.FromMilliseconds(380)) { EasingFunction = new SpringEase { Damping = .8 }, FillBehavior = FillBehavior.Stop });
        }
        slider.Loaded += (_, _) => Clip(); slider.SizeChanged += (_, _) => Clip();
        slider.AddHandler(PreviewMouseLeftButtonDownEvent, new MouseButtonEventHandler((_, e) =>
        {
            grab = e.GetPosition(slider); moved = false;
            double current = slider.Value; slider.BeginAnimation(Slider.ValueProperty, null); slider.Value = current; grabValue = current;
            slider.CaptureMouse(); e.Handled = true;
            Scale(1.04, 1.04, true);
        }), true);
        slider.AddHandler(PreviewMouseMoveEvent, new MouseEventHandler((_, e) =>
        {
            if (!slider.IsMouseCaptured) return;
            double travel = Travel(e.GetPosition(slider));
            if (!moved && Math.Abs(travel) < 3) return;
            moved = true;
            double raw = grabValue + travel / Length() * Range();
            slider.Value = Math.Clamp(raw, slider.Minimum, slider.Maximum);
            // Rubber band past the ends (Apple's x·c / (x·c + d) curve), growing out of the end being pulled.
            double overshoot = raw > slider.Maximum ? raw - slider.Maximum : raw < slider.Minimum ? slider.Minimum - raw : 0;
            double pixels = overshoot / Range() * Length();
            double band = (1 - 1 / (pixels * .55 / Length() + 1)) * .16;
            slider.RenderTransformOrigin = raw > slider.Maximum ? (vertical ? new Point(.5, 1) : new Point(0, .5)) : raw < slider.Minimum ? (vertical ? new Point(.5, 0) : new Point(1, .5)) : new Point(.5, .5);
            Scale(1.04 + band, 1.04 - band * .45, false);
        }), true);
        slider.AddHandler(PreviewMouseLeftButtonUpEvent, new MouseButtonEventHandler((_, e) =>
        {
            if (!slider.IsMouseCaptured) return;
            slider.ReleaseMouseCapture(); e.Handled = true;
            if (!moved) Glide(ValueAt(e.GetPosition(slider)));
            Scale(1, 1, true);
        }), true);
        slider.LostMouseCapture += (_, _) => { if (stretch.ScaleX != 1 || stretch.ScaleY != 1) Scale(1, 1, true); };
    }
    private FrameworkElement PanelFor(IslandView target) => target switch
    {
        IslandView.Home => MediaPanel, IslandView.Control => DesktopPanel, IslandView.Scene => WallpaperCard,
        IslandView.AirPlay => AirPlayCard, IslandView.Settings => SettingsCard, _ => PairingPanel,
    };
    /// <summary>Switches the expanded island to one horizontal view; the shape springs to the new view's height.</summary>
    public void ShowView(IslandView next)
    {
        bool changed = next != view; view = next;
        foreach (var candidate in Enum.GetValues<IslandView>()) PanelFor(candidate).Visibility = candidate == next ? Visibility.Visible : Visibility.Collapsed;
        if (next == IslandView.Control) RefreshMixer();
        SelectTab();
        if (!IsExpanded) return;
        AnimateSize(IslandModel.ExpandedWidth, ExpandedHeight, true);
        if (changed) { var panel = PanelFor(next); panel.Opacity = 0; Fade(panel, 1, 40, IslandModel.ContentFadeMs, .98, 8); }
    }
    private void SelectTab()
    {
        var idle = (Brush)FindResource("ModuleBrush"); var active = (Brush)FindResource("FillHoverBrush");
        foreach (var (tab, target) in new[] { (HomeTab, IslandView.Home), (ControlTab, IslandView.Control), (SceneTab, IslandView.Scene), (AirPlayTab, IslandView.AirPlay), (SettingsTab, IslandView.Settings) })
            tab.Background = target == view ? active : idle;
    }
    private void TabClick(object sender, RoutedEventArgs e) { if (sender is Button { Tag: string name } && Enum.TryParse<IslandView>(name, out var target)) ShowView(target); }

    // Ambient "shader": the colour field behind the content takes the artwork's dominant colour and breathes slowly.
    private ImageSource? ambientSource;
    private bool ambientSet;
    private void UpdateAmbient(ImageSource? artwork)
    {
        if (ambientSet && ReferenceEquals(artwork, ambientSource)) return;
        ambientSource = artwork; ambientSet = true;
        var color = artwork is BitmapSource bitmap ? DominantColor(bitmap) : Color.FromRgb(0x3A, 0x4A, 0x9A);
        var duration = TimeSpan.FromMilliseconds(Settings.Animations ? 700 : 0);
        AmbientCore.BeginAnimation(GradientStop.ColorProperty, new ColorAnimation(color, duration));
        AmbientEdge.BeginAnimation(GradientStop.ColorProperty, new ColorAnimation(Color.FromArgb(0, color.R, color.G, color.B), duration));
    }
    private static Color DominantColor(BitmapSource source)
    {
        try
        {
            var small = new FormatConvertedBitmap(new TransformedBitmap(source, new ScaleTransform(12.0 / Math.Max(1, source.PixelWidth), 12.0 / Math.Max(1, source.PixelHeight))), PixelFormats.Bgra32, null, 0);
            int w = small.PixelWidth, h = small.PixelHeight; var pixels = new byte[w * h * 4]; small.CopyPixels(pixels, w * 4, 0);
            double r = 0, g = 0, b = 0, total = 0;
            for (int i = 0; i + 3 < pixels.Length; i += 4)
            {
                // Weight colourful pixels so a grey background does not wash out the tint.
                double pb = pixels[i], pg = pixels[i + 1], pr = pixels[i + 2];
                double weight = .08 + (Math.Max(pr, Math.Max(pg, pb)) - Math.Min(pr, Math.Min(pg, pb))) / 255.0;
                r += pr * weight; g += pg * weight; b += pb * weight; total += weight;
            }
            r /= total; g /= total; b /= total;
            double peak = Math.Max(1, Math.Max(r, Math.Max(g, b))), lift = 190 / peak;
            return Color.FromRgb((byte)Math.Min(255, r * lift), (byte)Math.Min(255, g * lift), (byte)Math.Min(255, b * lift));
        }
        catch (Exception error) { Log.Error("ambient colour", error); return Color.FromRgb(0x3A, 0x4A, 0x9A); }
    }
    private void Breathe(bool on)
    {
        var group = (TransformGroup)Ambient.RenderTransform; var scale = (ScaleTransform)group.Children[0]; var drift = (TranslateTransform)group.Children[1];
        DoubleAnimation? Loop(double from, double to, double seconds)
        {
            if (!on || !Settings.Animations) return null;
            var loop = new DoubleAnimation(from, to, TimeSpan.FromSeconds(seconds)) { AutoReverse = true, RepeatBehavior = RepeatBehavior.Forever, EasingFunction = new SineEase { EasingMode = EasingMode.EaseInOut } };
            Timeline.SetDesiredFrameRate(loop, 24); return loop;
        }
        scale.BeginAnimation(ScaleTransform.ScaleXProperty, Loop(1, 1.14, 5)); scale.BeginAnimation(ScaleTransform.ScaleYProperty, Loop(1, 1.08, 6.5));
        drift.BeginAnimation(TranslateTransform.XProperty, Loop(-18, 22, 8)); drift.BeginAnimation(TranslateTransform.YProperty, Loop(-8, 10, 7));
    }
    private async Task Initialize()
    {
        updating = true;
        AnimationToggle.IsChecked = Settings.Animations; FullscreenToggle.IsChecked = Settings.HideFullscreen;
        HoverToggle.IsChecked = Settings.HoverExpand; EcoToggle.IsChecked = Settings.EcoBrowsers; ReactiveToggle.IsChecked = Settings.AudioReactive; StartupToggle.IsChecked = DesktopService.StartupEnabled;
        AirPlayToggle.IsChecked = Settings.AirPlayEnabled; AirPlayPinToggle.IsChecked = Settings.AirPlayRequirePin;
        AirPlayVideoFullscreen.IsChecked = Settings.AirPlayVideoFullscreen;
        AirPlayVideoAspect.SelectedIndex = Settings.AirPlayVideoKeepAspect ? 0 : 1;
        AirPlayVideoBuffer.SelectedIndex = Settings.AirPlayVideoBufferSeconds <= 2 ? 0 : Settings.AirPlayVideoBufferSeconds >= 8 ? 2 : 1;
        PopulateMonitors(); updating = false;
        tray = new Forms.NotifyIcon { Icon = CreateTrayIcon(), Text = "Island Desktop · Windows", Visible = true };
        tray.MouseClick += (_, e) => { if (e.Button == Forms.MouseButtons.Left) Dispatcher.Invoke(() => Expand()); };
        var trayMenu = new Forms.ContextMenuStrip();
        trayMenu.Items.Add("Відкрити", null, (_, _) => Dispatcher.Invoke(() => Expand()));
        trayMenu.Items.Add("Керування ПК", null, (_, _) => Dispatcher.Invoke(() => { Expand(); ShowDesktop(); }));
        trayMenu.Items.Add("Закрити", null, (_, _) => Dispatcher.Invoke(() => System.Windows.Application.Current.Shutdown()));
        tray.ContextMenuStrip = trayMenu;
        Media.Changed += () => Dispatcher.Invoke(UpdateMedia);
        AirPlay.Changed += async () => { UpdateAirPlay(); await Media.Refresh(); };
        await Media.Initialize(); Audio.Reactive(Settings.AudioReactive);
        _ = AirPlay.SetEnabled(Settings.AirPlayEnabled, Settings.AirPlayRequirePin); UpdateAirPlay();
        initialized = true; Position(); await Tick(); Shell = new DesktopShell(this); timer.Start(); waveTimer.Start();
        Launchpad.Prewarm();
        eco = new EcoMode(Settings.EcoBrowsers);
        eco.Changed += count => Dispatcher.BeginInvoke(() => EcoState.Text = !Settings.EcoBrowsers ? "" : count > 0 ? $"Зараз приглушено процесів браузера: {count}" : "Браузер на передньому плані або закритий");
        // Build the expanded tree once (it stays clipped and transparent) so the first open does not stall on templates.
        if (!IsExpanded) { Expanded.Visibility = Visibility.Visible; Expanded.UpdateLayout(); Expanded.Visibility = Visibility.Collapsed; }
    }
    private static System.Drawing.Icon CreateTrayIcon()
    {
        using var bitmap = new System.Drawing.Bitmap(32, 32);
        using var g = System.Drawing.Graphics.FromImage(bitmap); g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
        g.Clear(System.Drawing.Color.Transparent);
        using var background = new System.Drawing.SolidBrush(System.Drawing.Color.FromArgb(5, 6, 9)); g.FillEllipse(background, 1, 1, 30, 30);
        using var accent = new System.Drawing.SolidBrush(System.Drawing.Color.FromArgb(157, 217, 188));
        g.FillEllipse(accent, 8, 12, 6, 8); g.FillEllipse(accent, 18, 12, 6, 8);
        IntPtr icon = bitmap.GetHicon(); var result = (System.Drawing.Icon)System.Drawing.Icon.FromHandle(icon).Clone(); DestroyIcon(icon); return result;
    }
    [System.Runtime.InteropServices.DllImport("user32.dll")] private static extern bool DestroyIcon(IntPtr icon);
    private async Task Tick()
    {
        // Status polling does COM/process work on the UI thread; never let it stall a morph mid-flight.
        if (tickBusy || DateTime.UtcNow < morphBusyUntil) return; tickBusy = true;
        try
        {
            var perf = UiPerf.Start(); await Media.Refresh(); UiPerf.Report("tick.media(with await)", perf);
            var remaining = IslandModel.Remaining(Settings.FocusUntil, DateTimeOffset.Now);
            Clock.Text = remaining > TimeSpan.Zero ? $"{(int)remaining.TotalMinutes:00}:{remaining.Seconds:00}" : DateTime.Now.ToString("HH:mm");
            ExpandedClock.Text = DateTime.Now.ToString("HH:mm");
            var today = DateTime.Now.ToString("dddd, d MMMM", Ukrainian); TodayDate.Text = char.ToUpper(today[0]) + today[1..];
            FocusState.Text = remaining > TimeSpan.Zero ? $"Залишилось {(int)remaining.TotalMinutes:00}:{remaining.Seconds:00}" : "Час для зосередженої роботи";
            if (Settings.FocusUntil.HasValue && remaining == TimeSpan.Zero)
            {
                Settings.FocusUntil = null; Settings.Save();
                FocusState.Text = "Фокус завершено · час зробити паузу";
            }
            perf = UiPerf.Start(); RefreshAudio(); UiPerf.Report("tick.audio", perf);
            if (DateTimeOffset.UtcNow >= nextWallpaper) { nextWallpaper = DateTimeOffset.UtcNow.AddSeconds(5); perf = UiPerf.Start(); var refreshing = Desktop.RefreshWallpaper(); UiPerf.Report("tick.wallpaper(sync part)", perf); await refreshing; perf = UiPerf.Start(); UpdateWallpaper(); UiPerf.Report("tick.updateWallpaper", perf); }
            perf = UiPerf.Start(); bool hidden = locked || Settings.HideFullscreen && DesktopService.Fullscreen(handle); UiPerf.Report("tick.fullscreen", perf);
            if (hidden && IsVisible) { Collapse(); Hide(); }
            else if (!hidden && !IsVisible) Show();
        }
        catch (Exception e) { Log.Error("tick", e); }
        finally { tickBusy = false; }
    }
    private void UpdateMedia()
    {
        if (!Dispatcher.CheckAccess()) { Dispatcher.InvokeAsync(UpdateMedia); return; }
        updating = true;
        var state = Media.State;
        TrackTitle.Text = state.Title; Artist.Text = state.Artist;
        Art.Source = MiniArt.Source = state.Artwork; UpdateAmbient(state.Artwork); ArtFallback.Visibility = MiniFallback.Visibility = state.Artwork == null ? Visibility.Visible : Visibility.Collapsed;
        MiniFallback.Visibility = !state.Available && !Settings.FocusUntil.HasValue ? Visibility.Collapsed : MiniFallback.Visibility;
        Wave.Visibility = state.Available || Settings.AudioReactive ? Visibility.Visible : Visibility.Hidden;
        Previous.IsEnabled = state.CanPrevious; Next.IsEnabled = state.CanNext; PlayPause.IsEnabled = state.CanToggle;
        ((TextBlock)PlayPause.Content).Text = state.Playing ? "\uE769" : "\uE768";
        if (!seeking) { Seek.Minimum = state.Start; Seek.Maximum = Math.Max(state.Start + 1, state.End); Seek.Value = state.Position; }
        Seek.IsEnabled = state.CanSeek && state.End > state.Start;
        Elapsed.Text = FormatTime(state.Position); Duration.Text = state.End > state.Start ? FormatTime(state.End) : "";
        var receiver = AirPlay.State;
        VideoExpand.Visibility = state.Source == AirPlayService.SourceId && receiver.VideoWindow ? Visibility.Visible : Visibility.Collapsed;
        VideoExpand.Content = receiver.VideoFullscreen ? "У вікно ↙" : "Розгорнути ↗";
        MediaHint.Text = Media.Error ?? (state.Source == AirPlayService.SourceId ? receiver.Kind == "video" ? receiver.BufferPercent < 100 ? $"AirPlay · буфер {receiver.BufferPercent}%" : "Відео з твого пристрою · AirPlay" : state.CanToggle ? "Музика з твого пристрою · AirPlay" : "AirPlay · керуй відтворенням на своєму пристрої" : state.Available ? "Керує поточним плеєром Windows" : "Запусти плеєр або підключи iPhone через AirPlay.");
        string key = string.Join("|", Media.Choices.Select(c => c.Id + c.Name));
        if (key != choicesKey)
        {
            var old = PlayerChoice.SelectedValue as string; choicesKey = key;
            PlayerChoice.ItemsSource = new[] { new SessionChoice("", "Автоматичний вибір плеєра") }.Concat(Media.Choices).ToArray();
            PlayerChoice.SelectedValue = Media.Choices.Any(c => c.Id == old) ? old : "";
        }
        if (PlayerChoice.SelectedIndex < 0) PlayerChoice.SelectedIndex = 0;
        updating = false; Wave.InvalidateVisual();
    }
    private static string FormatTime(double seconds) { var t = TimeSpan.FromSeconds(Math.Max(0, seconds)); return t.TotalHours >= 1 ? $"{(int)t.TotalHours}:{t.Minutes:00}:{t.Seconds:00}" : $"{(int)t.TotalMinutes}:{t.Seconds:00}"; }
    private string shownPin = "";
    private void UpdateAirPlay()
    {
        var state = AirPlay.State;
        AirPlayState.Text = state.Error ?? state.Status;
        AirPlayName.Text = state.Name;
        AirPlayCode.Text = state.Pin; AirPlayCodePanel.Visibility = state.Pin.Length > 0 ? Visibility.Visible : Visibility.Collapsed;
        AirPlayToggle.IsChecked = state.Enabled;
        PairingPin.Text = state.Pin;
        if (state.Pin.Length > 0 && shownPin != state.Pin)
        {
            Expand(false); ShowView(IslandView.Pairing);
        }
        else if (state.Pin.Length == 0 && view == IslandView.Pairing) ShowMedia();
        shownPin = state.Pin;
    }
    public async Task<bool> SetAirPlay(bool enabled)
    {
        Settings.AirPlayEnabled = enabled; Settings.Save();
        return await AirPlay.SetEnabled(enabled, Settings.AirPlayRequirePin);
    }
    public async Task<bool> SetAirPlayPin(bool value)
    {
        Settings.AirPlayRequirePin = value; Settings.Save(); AirPlayPinToggle.IsChecked = value;
        return !Settings.AirPlayEnabled || await AirPlay.Restart(value);
    }
    private async void AirPlayChanged(object sender, RoutedEventArgs e) { if (!updating && initialized) await SetAirPlay(AirPlayToggle.IsChecked == true); }
    private async void AirPlayPinChanged(object sender, RoutedEventArgs e) { if (!updating && initialized) await SetAirPlayPin(AirPlayPinToggle.IsChecked == true); }
    private async void AirPlayRestartClick(object sender, RoutedEventArgs e) { if (initialized) { await SetAirPlay(false); await SetAirPlay(true); } }
    public async Task<bool> SetAirPlayVideo(bool? fullscreen = null, bool? keepAspect = null, int? bufferSeconds = null)
    {
        if (bufferSeconds.HasValue && bufferSeconds.Value is not (2 or 5 or 8)) return false;
        Settings.AirPlayVideoFullscreen = fullscreen ?? Settings.AirPlayVideoFullscreen;
        Settings.AirPlayVideoKeepAspect = keepAspect ?? Settings.AirPlayVideoKeepAspect;
        Settings.AirPlayVideoBufferSeconds = bufferSeconds ?? Settings.AirPlayVideoBufferSeconds;
        Settings.Save(); updating = true;
        AirPlayVideoFullscreen.IsChecked = Settings.AirPlayVideoFullscreen;
        AirPlayVideoAspect.SelectedIndex = Settings.AirPlayVideoKeepAspect ? 0 : 1;
        AirPlayVideoBuffer.SelectedIndex = Settings.AirPlayVideoBufferSeconds == 2 ? 0 : Settings.AirPlayVideoBufferSeconds == 8 ? 2 : 1;
        updating = false;
        return !Settings.AirPlayEnabled || await AirPlay.ApplyVideoOptions();
    }
    private async void AirPlayVideoChanged(object sender, RoutedEventArgs e)
    { if (!updating && initialized) await SetAirPlayVideo(AirPlayVideoFullscreen.IsChecked == true); }
    private async void AirPlayVideoSelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!updating && initialized && AirPlayVideoAspect.SelectedIndex >= 0 && AirPlayVideoBuffer.SelectedIndex >= 0)
            await SetAirPlayVideo(keepAspect: AirPlayVideoAspect.SelectedIndex == 0, bufferSeconds: new[] { 2, 5, 8 }[AirPlayVideoBuffer.SelectedIndex]);
    }
    private async void VideoExpandClick(object sender, RoutedEventArgs e)
    { if (await SetAirPlayVideo(!AirPlay.State.VideoFullscreen) && Settings.AirPlayVideoFullscreen) Collapse(); }
    public void ShowAirPlay() { Expand(false); ShowView(IslandView.AirPlay); }
    private void RefreshAudio()
    {
        var state = Audio.Read(); updating = true;
        if (!Volume.IsMouseCaptureWithin && !Volume.IsKeyboardFocusWithin) Volume.Value = state.Volume * 100;
        Volume.IsEnabled = Mute.IsEnabled = state.Available; VolumeText.Text = $"{state.Volume * 100:0}%";
        ((TextBlock)Mute.Content).Text = state.Muted ? "\uE74F" : "\uE767"; Route.Text = state.Device; updating = false;
    }
    private void UpdateWallpaper()
    {
        var state = Desktop.Wallpaper;
        WallpaperState.Text = state.Connected ? $" {(state.Paused ? "пауза, робочий стіл перекритий" : "працює")}\nPip: {TranslateState(state.State)}" : state.LivelyRunning ? "Lively працює. Сервер V6 зараз недоступний." : "Lively зараз не запущений.";
        var preferences = Desktop.ReadWallpaperPreferences(); updating = true;
        WaterToggle.IsEnabled = WallpaperQuality.IsEnabled = WallpaperTime.IsEnabled = preferences.Ready;
        WaterToggle.IsChecked = preferences.Water; WallpaperQuality.SelectedIndex = preferences.Quality; WallpaperTime.SelectedIndex = preferences.TimeOfDay;
        updating = false;
    }
    private static string TranslateState(string state) => state switch { "working" => "працює", "editing" => "редагує", "testing" => "тестує", "failed" => "помилка", "permission" => "чекає дозволу", "done" => "завершив", "browsing" => "переглядає", "starting" => "починає", _ => "відпочиває" };
    // Dynamic Island choreography: the shape leads, content follows it out and leaves before it on the way back.
    public void Expand(bool activate = true)
    {
        if (locked) return;
        if (!IsVisible) Show();
        bool opening = !IsExpanded;
        IsExpanded = true;
        AnimateSize(IslandModel.ExpandedWidth, ExpandedHeight, true);
        if (opening)
        {
            Compact.IsHitTestVisible = false; Fade(Compact, 0, 0, IslandModel.ContentOutMs);
            Expanded.Visibility = Visibility.Visible; Fade(Expanded, 1, IslandModel.ContentDelayMs, IslandModel.ContentFadeMs, .94, -10); Breathe(true);
        }
        if (activate) { SetActivation(true); Activate(); }
    }
    public void Collapse()
    {
        if (!IsExpanded) return;
        IsExpanded = false; hoverTimer.Stop(); leaveTimer.Stop();
        Fade(Expanded, 0, 0, IslandModel.ContentOutMs, .97, -6, () => { if (!IsExpanded) { Expanded.Visibility = Visibility.Collapsed; Breathe(false); } });
        MorphTo(IslandModel.CompactWidth, IslandModel.CompactHeight, IslandModel.CompactRadius, false, IslandModel.CloseDelayMs);
        Compact.IsHitTestVisible = true; Fade(Compact, 1, IslandModel.CloseDelayMs + IslandModel.CloseMs / 2, IslandModel.ContentFadeMs);
        SetActivation(false);
    }
    private const double HeaderHeight = 56;
    private static readonly System.Globalization.CultureInfo Ukrainian = new("uk-UA");
    /// <summary>Every view is a horizontal strip; the island height follows the active view's content.</summary>
    private double ExpandedHeight
    {
        get
        {
            var panel = PanelFor(view);
            panel.Measure(new Size(IslandModel.ExpandedWidth, double.PositiveInfinity));
            return Math.Clamp(Math.Ceiling(HeaderHeight + panel.DesiredSize.Height), 140, IslandModel.StageHeight - 40);
        }
    }
    /// <summary>Fades an element; entering content settles from (scale, offset) to rest, leaving content drifts towards them.</summary>
    private void Fade(FrameworkElement element, double opacity, int delayMs, int durationMs, double scale = 1, double offset = 0, Action? done = null)
    {
        if (!Settings.Animations) { delayMs = 0; durationMs = 0; }
        var ease = new CubicEase { EasingMode = EasingMode.EaseOut };
        var begin = TimeSpan.FromMilliseconds(delayMs); var duration = TimeSpan.FromMilliseconds(durationMs);
        var fade = new DoubleAnimation(opacity, duration) { BeginTime = begin, EasingFunction = ease };
        if (done != null) fade.Completed += (_, _) => done();
        element.BeginAnimation(OpacityProperty, fade);
        if (element.RenderTransform is not TransformGroup group || group.Children.Count < 2) return;
        bool entering = opacity > 0;
        var scaleTransform = (ScaleTransform)group.Children[0]; var offsetTransform = (TranslateTransform)group.Children[1];
        var scaleAnimation = entering ? new DoubleAnimation(scale, 1, duration) : new DoubleAnimation(scale, duration);
        var offsetAnimation = entering ? new DoubleAnimation(offset, 0, duration) : new DoubleAnimation(offset, duration);
        scaleAnimation.BeginTime = offsetAnimation.BeginTime = begin; scaleAnimation.EasingFunction = offsetAnimation.EasingFunction = ease;
        scaleTransform.BeginAnimation(ScaleTransform.ScaleXProperty, scaleAnimation); scaleTransform.BeginAnimation(ScaleTransform.ScaleYProperty, scaleAnimation);
        offsetTransform.BeginAnimation(TranslateTransform.YProperty, offsetAnimation);
    }
    private void SetActivation(bool enabled)
    {
        if (handle == IntPtr.Zero) return;
        var style = GetWindowLongPtr(handle, -20).ToInt64();
        SetWindowLongPtr(handle, -20, new IntPtr(enabled ? style & ~0x08000000L : style | 0x08000000L));
    }
    [System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")] private static extern IntPtr GetWindowLongPtr(IntPtr window, int index);
    [System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW")] private static extern IntPtr SetWindowLongPtr(IntPtr window, int index, IntPtr value);
    private void AnimateSize(double width, double height, bool opening)
    {
        // Content keeps its final height so the growing shape reveals it instead of reflowing it every frame.
        Expanded.Height = height;
        MorphTo(width, height, IslandModel.ExpandedRadius, opening);
    }

    // The window is a fixed transparent stage and never moves or resizes (resizing a layered window per frame
    // is what made the old island stutter). One clock drives width, height and corner radius through a spring.
    public static readonly DependencyProperty MorphProperty = DependencyProperty.Register(nameof(Morph), typeof(double), typeof(MainWindow), new PropertyMetadata(1.0, (d, _) => ((MainWindow)d).ApplyMorph()));
    public double Morph { get => (double)GetValue(MorphProperty); set => SetValue(MorphProperty, value); }
    private static readonly (double Width, double Height, double Radius) CompactShape = (IslandModel.CompactWidth, IslandModel.CompactHeight, IslandModel.CompactRadius);
    private (double Width, double Height, double Radius) morphFrom = CompactShape, morphTo = CompactShape, shape = CompactShape;
    private double morphDamping = 1;
    private int morphGeneration;
    private DateTime morphBusyUntil;
    private void MorphTo(double width, double height, double radius, bool opening, int delayMs = 0)
    {
        int generation = ++morphGeneration;
        BeginAnimation(MorphProperty, null);
        morphFrom = shape; morphTo = (width, height, radius); morphDamping = opening ? IslandModel.OpenDamping : IslandModel.CloseDamping;
        int duration = Settings.Animations ? opening ? IslandModel.OpenMs : IslandModel.CloseMs : 0;
        if (duration == 0) { Morph = 1; ApplyMorph(); return; }
        Morph = 0; morphBusyUntil = DateTime.UtcNow.AddMilliseconds(delayMs + duration + 120);
        var clock = new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(duration)) { BeginTime = TimeSpan.FromMilliseconds(delayMs) };
        clock.Completed += (_, _) => { if (generation == morphGeneration) { BeginAnimation(MorphProperty, null); Morph = 1; } };
        BeginAnimation(MorphProperty, clock);
    }
    private void ApplyMorph()
    {
        double k = IslandModel.Spring(Morph, morphDamping);
        double width = Math.Max(1, morphFrom.Width + (morphTo.Width - morphFrom.Width) * k);
        double height = Math.Max(1, morphFrom.Height + (morphTo.Height - morphFrom.Height) * k);
        double radius = morphFrom.Radius + (morphTo.Radius - morphFrom.Radius) * Math.Clamp(k, 0, 1);
        radius = Math.Min(radius, Math.Min(width, height) / 2);
        shape = (width, height, radius);
        // Continuous corners, an antialiased fill and a light rim read much softer than a hard rounded-rect clip.
        var outline = IslandModel.Squircle(width, height, radius);
        Surface.Width = width; Surface.Height = height;
        ShapeFill.Data = ShapeRim.Data = ShapeShadow.Data = outline; SurfaceContent.Clip = outline;
        double open = Math.Clamp((width - IslandModel.CompactWidth) / (IslandModel.ExpandedWidth - IslandModel.CompactWidth), 0, 1);
        ShapeRim.Opacity = open; ShapeShadow.Opacity = .65 * open; ShapeShadow.Visibility = open > .02 ? Visibility.Visible : Visibility.Hidden;
    }
    private void Position()
    {
        var screens = Forms.Screen.AllScreens;
        var screen = Settings.Monitor >= 0 && Settings.Monitor < screens.Length ? screens[Settings.Monitor] : Forms.Screen.PrimaryScreen!;
        double scale = PresentationSource.FromVisual(this)?.CompositionTarget?.TransformFromDevice.M11 ?? 1;
        center = (screen.Bounds.Left + screen.Bounds.Width / 2.0) * scale;
        Width = IslandModel.StageWidth; Height = IslandModel.StageHeight;
        Left = center - Width / 2; Top = screen.WorkingArea.Top * scale + IslandModel.Clamp(Settings.Offset, 0, 150);
    }
    private void PopulateMonitors()
    {
        var choices = new[] { new { Index = -1, Name = "Основний екран" } }.Concat(Forms.Screen.AllScreens.Select((s, i) => new { Index = i, Name = $"Екран {i + 1} · {s.Bounds.Width} × {s.Bounds.Height}" })).ToArray();
        MonitorChoice.ItemsSource = choices; MonitorChoice.SelectedValue = Settings.Monitor;
    }
    protected override void OnDpiChanged(DpiScale oldDpi, DpiScale newDpi)
    {
        base.OnDpiChanged(oldDpi, newDpi);
        Dispatcher.InvokeAsync(Position);
    }
    private void DisplayChanged(object? sender, EventArgs e) => Dispatcher.InvokeAsync(() => { updating = true; PopulateMonitors(); updating = false; Position(); });
    private void SessionSwitch(object sender, SessionSwitchEventArgs e) => Dispatcher.InvokeAsync(() =>
    {
        if (e.Reason == SessionSwitchReason.SessionLock) { locked = true; Collapse(); Audio.Reactive(false); Hide(); }
        else if (e.Reason == SessionSwitchReason.SessionUnlock) { locked = false; Audio.Reactive(Settings.AudioReactive); Show(); Position(); }
    });
    public void StartFocus(int seconds) { Settings.FocusUntil = DateTimeOffset.Now.AddSeconds(Math.Clamp(seconds, 1, 8 * 3600)); Settings.Save(); }
    public void ShowMedia() => ShowView(IslandView.Home);
    public void ShowDesktop() => ShowView(IslandView.Control);
    public void ScrollSettings() => ShowView(IslandView.Settings);
    private void RefreshMixer()
    {
        Mixer.Children.Clear(); var state = Audio.Read(true);
        if (state.Apps.Length == 0) Mixer.Children.Add(new TextBlock { Text = "Поки немає активних аудіопрограм", FontSize = 12, Foreground = (Brush)FindResource("MutedBrush"), Margin = new Thickness(0, 2, 0, 4) });
        foreach (var app in state.Apps.GroupBy(a => a.Pid).Select(g => g.First()))
        {
            // One Control Center slab per app: glyph and name inside the slider, round mute button beside it.
            var row = new Grid { Margin = new Thickness(0, 0, 0, 8) };
            row.ColumnDefinitions.Add(new ColumnDefinition()); row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(48) });
            var slider = new Slider { Style = (Style)FindResource("PillSlider"), Tag = "\uE767", Height = 40, Minimum = 0, Maximum = 100, Value = app.Volume * 100, ToolTip = "Гучність " + app.Name };
            Volumetric(slider);
            slider.ValueChanged += (_, _) => { if (!Audio.SetVolume(slider.Value / 100, app.Pid)) MediaHint.Text = "Аудіопрограма вже закрилась"; };
            var name = new TextBlock { Text = app.Name, FontSize = 12, FontWeight = FontWeights.SemiBold, Foreground = (Brush)FindResource("MutedBrush"), Margin = new Thickness(38, 0, 12, 0), VerticalAlignment = VerticalAlignment.Center, TextTrimming = TextTrimming.CharacterEllipsis, IsHitTestVisible = false };
            var mute = new Button { Style = (Style)FindResource("Round"), Width = 40, Height = 40, HorizontalAlignment = HorizontalAlignment.Right, Background = (Brush)FindResource("FillBrush"), ToolTip = "Тиша для " + app.Name };
            var glyph = MakeIcon(app.Muted ? "\uE74F" : "\uE767", 14); mute.Content = glyph; Grid.SetColumn(mute, 1);
            bool muted = app.Muted; mute.Click += (_, _) => { if (Audio.SetMute(!muted, app.Pid)) { muted = !muted; glyph.Text = muted ? "\uE74F" : "\uE767"; } };
            row.Children.Add(slider); row.Children.Add(name); row.Children.Add(mute); Mixer.Children.Add(row);
        }
    }
    public void Snapshot(string path)
    {
        UpdateLayout(); double dpi = VisualTreeHelper.GetDpi(this).DpiScaleX;
        double width = Surface.ActualWidth, height = Surface.ActualHeight;
        var visual = new DrawingVisual(); using (var context = visual.RenderOpen()) context.DrawRectangle(new VisualBrush(Surface), null, new Rect(0, 0, width, height));
        var bitmap = new RenderTargetBitmap((int)Math.Ceiling(width * dpi), (int)Math.Ceiling(height * dpi), 96 * dpi, 96 * dpi, PixelFormats.Pbgra32);
        bitmap.Render(visual); var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!); using var file = File.Create(path); encoder.Save(file);
    }
    private void CompactClick(object sender, MouseButtonEventArgs e) { Expand(); e.Handled = true; }
    private void CompactEnter(object sender, MouseEventArgs e) { if (Settings.HoverExpand) hoverTimer.Start(); }
    private void CompactLeave(object sender, MouseEventArgs e) => hoverTimer.Stop();
    private void CompactWheel(object sender, MouseWheelEventArgs e) { var value = Audio.Read(); Audio.SetVolume(value.Volume + (e.Delta > 0 ? .05 : -.05)); RefreshAudio(); e.Handled = true; }
    private void CollapseClick(object sender, RoutedEventArgs e) => Collapse();
    private async void PlayClick(object sender, RoutedEventArgs e) => await RunCommand("playpause");
    private async void NextClick(object sender, RoutedEventArgs e) => await RunCommand("next");
    private async void PreviousClick(object sender, RoutedEventArgs e) => await RunCommand("previous");
    private async Task RunCommand(string command) { if (!await Media.Command(command)) MediaHint.Text = "Плеєр не підтримує цю дію"; }
    private void SeekStart(object sender, MouseButtonEventArgs e) => seeking = true;
    private async void SeekEnd(object sender, MouseButtonEventArgs e) { if (!await Media.Command("seek", Seek.Value)) MediaHint.Text = "Перемотування недоступне"; seeking = false; }
    private async void SeekKey(object sender, KeyEventArgs e) { if (e.Key is Key.Left or Key.Right or Key.Home or Key.End) await Media.Command("seek", Seek.Value); }
    private void VolumeChanged(object sender, RoutedPropertyChangedEventArgs<double> e) { if (!updating && initialized) { Audio.SetVolume(Volume.Value / 100); VolumeText.Text = $"{Volume.Value:0}%"; } }
    private void MuteClick(object sender, RoutedEventArgs e) { Audio.SetMute(!Audio.Read().Muted); RefreshAudio(); }
    private async void PlayerChanged(object sender, SelectionChangedEventArgs e) { if (!updating && initialized) { Media.Select(PlayerChoice.SelectedValue as string); await Media.Refresh(); } }
    private void Focus25Click(object sender, RoutedEventArgs e) => StartFocus(25 * 60);
    private void Focus50Click(object sender, RoutedEventArgs e) => StartFocus(50 * 60);
    private void StopFocusClick(object sender, RoutedEventArgs e) { Settings.FocusUntil = null; Settings.Save(); }
    private void RefreshMixerClick(object sender, RoutedEventArgs e) => RefreshMixer();
    private void PreferencesChanged(object sender, RoutedEventArgs e)
    {
        Settings.Animations = AnimationToggle.IsChecked == true; Settings.HideFullscreen = FullscreenToggle.IsChecked == true; Settings.HoverExpand = HoverToggle.IsChecked == true;
        bool reactive = ReactiveToggle.IsChecked == true; if (Settings.AudioReactive != reactive) { Settings.AudioReactive = reactive; Audio.Reactive(reactive); }
        Settings.EcoBrowsers = EcoToggle.IsChecked == true; if (eco != null) eco.Enabled = Settings.EcoBrowsers;
        Settings.Save(); Wave.InvalidateVisual();
    }
    private void StartupChanged(object sender, RoutedEventArgs e) { if (!updating) { try { DesktopService.SetStartup(StartupToggle.IsChecked == true); } catch (Exception error) { Log.Error("startup", error); StartupToggle.IsChecked = DesktopService.StartupEnabled; } } }
    private void MonitorChanged(object sender, SelectionChangedEventArgs e) { if (!updating && initialized && MonitorChoice.SelectedValue is int index) { Settings.Monitor = index; Settings.Save(); Position(); } }
    private void YouTubeClick(object sender, RoutedEventArgs e) => DesktopService.Browser("youtube");
    private void NetflixClick(object sender, RoutedEventArgs e) => DesktopService.Browser("netflix");
    private void LivelyClick(object sender, RoutedEventArgs e) => DesktopService.OpenLively();
    private async void WaterChanged(object sender, RoutedEventArgs e) { if (!updating && initialized && !await Desktop.WallpaperProperty("water", WaterToggle.IsChecked == true ? 1 : 0)) WallpaperState.Text = "Не вдалося змінити воду в Lively"; }
    private async void WallpaperQualityChanged(object sender, SelectionChangedEventArgs e) { if (!updating && initialized && !await Desktop.WallpaperProperty("quality", WallpaperQuality.SelectedIndex)) WallpaperState.Text = "Не вдалося змінити якість у Lively"; }
    private async void WallpaperTimeChanged(object sender, SelectionChangedEventArgs e) { if (!updating && initialized && !await Desktop.WallpaperProperty("timeOfDay", WallpaperTime.SelectedIndex)) WallpaperState.Text = "Не вдалося змінити освітлення в Lively"; }
    private void SoundSettingsClick(object sender, RoutedEventArgs e) => DesktopService.Open("ms-settings:sound");
    private void NotificationsClick(object sender, RoutedEventArgs e) => DesktopService.Open("ms-settings:notifications");
    private void ExitClick(object sender, RoutedEventArgs e) => System.Windows.Application.Current.Shutdown();
    private void Cleanup()
    {
        eco?.Dispose(); Shell?.Dispose(); timer.Stop(); waveTimer.Stop(); hoverTimer.Stop(); leaveTimer.Stop();
        SystemEvents.SessionSwitch -= SessionSwitch; SystemEvents.DisplaySettingsChanged -= DisplayChanged;
        Media.Dispose(); AirPlay.Dispose(); Audio.Dispose(); if (tray != null) { tray.Visible = false; tray.Icon?.Dispose(); tray.Dispose(); }
    }
}
