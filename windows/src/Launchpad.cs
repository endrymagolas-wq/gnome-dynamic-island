using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;

namespace Island.Windows;

public sealed class LaunchApp(string name, string parsingName)
{
    public string Name { get; } = name;
    /// <summary>Path inside shell:AppsFolder (an AUMID for Store apps, a known-folder path for desktop apps).</summary>
    public string ParsingName { get; } = parsingName;
    public ImageSource? Icon { get; set; }
}

/// <summary>
/// Apple-style launcher that replaces the Windows Start menu behind the dock's "Програми" button:
/// a Spotlight search field over a Launchpad grid of every app in shell:AppsFolder, in the island's visual language.
/// </summary>
public sealed class Launchpad : Window
{
    private const double PanelWidth = 760, PanelHeight = 580, OuterMargin = 34, Columns = 6;
    private static Launchpad? current;
    private static List<LaunchApp>? catalog;
    private static Task<List<LaunchApp>>? loading;
    private static event Action<LaunchApp>? IconLoaded;

    /// <summary>Starts reading the app catalog and icons in the background so the first open is instant.</summary>
    public static void Prewarm() => loading ??= LoadCatalog();

    public static void Toggle()
    {
        if (current is { IsVisible: true }) { current.Dismiss(); return; }
        current = new Launchpad(); current.Show(); current.Activate();
    }

    private readonly Grid panel = new() { Width = PanelWidth, Height = PanelHeight };
    private readonly Path fill = new(), rim = new(), shadow = new();
    private readonly TextBox search = new();
    private readonly TextBlock placeholder = new(), caption = new();
    private readonly WrapPanel grid = new() { ItemWidth = (PanelWidth - 52) / Columns, ItemHeight = 126 };
    private readonly ScrollViewer scroller = new();
    private readonly ScaleTransform zoom = new(.94, .94);
    private readonly TranslateTransform lift = new(0, 14);
    private readonly Dictionary<LaunchApp, (Button Tile, Image Image, Border Placeholder)> tiles = new();
    private List<LaunchApp> visible = new();
    private int selected;
    private bool closing;

    private Launchpad()
    {
        Title = "Island · Програми"; WindowStyle = WindowStyle.None; AllowsTransparency = true; Background = Brushes.Transparent;
        Topmost = true; ShowInTaskbar = false; ResizeMode = ResizeMode.NoResize; UseLayoutRounding = true;
        Width = PanelWidth + OuterMargin * 2; Height = PanelHeight + OuterMargin * 2;
        var area = SystemParameters.WorkArea;
        Left = area.Left + (area.Width - Width) / 2; Top = area.Top + Math.Max(0, (area.Height - Height) / 2 - 24);
        Content = BuildPanel();
        Loaded += async (_, _) => { Appear(); search.Focus(); await Populate(); };
        Deactivated += (_, _) => Dismiss();
        PreviewKeyDown += OnKey;
        IconLoaded += OnIconLoaded;
        Closed += (_, _) => { IconLoaded -= OnIconLoaded; if (current == this) current = null; };
    }

    private UIElement BuildPanel()
    {
        var outline = IslandModel.Squircle(PanelWidth, PanelHeight, 34);
        shadow.Data = fill.Data = rim.Data = outline;
        shadow.Fill = Brushes.Black; shadow.Opacity = .55; shadow.IsHitTestVisible = false;
        shadow.Effect = new BlurEffect { Radius = 30 }; shadow.RenderTransform = new TranslateTransform(0, 12);
        fill.Fill = new LinearGradientBrush(Color.FromRgb(0x17, 0x17, 0x1A), Color.FromRgb(0x0C, 0x0C, 0x0E), 90);
        rim.StrokeThickness = 1; rim.IsHitTestVisible = false;
        rim.Stroke = new LinearGradientBrush(new GradientStopCollection { new(Color.FromArgb(0x40, 255, 255, 255), 0), new(Color.FromArgb(0x10, 255, 255, 255), .35), new(Color.FromArgb(0x06, 255, 255, 255), 1) }, 90);

        var content = new Grid { Clip = outline };
        content.Children.Add(Glow(Color.FromRgb(0x3A, 0x5A, 0xD0), HorizontalAlignment.Left, VerticalAlignment.Top, new Thickness(-180, -200, 0, 0), .42));
        content.Children.Add(Glow(Color.FromRgb(0x8E, 0x4D, 0xD8), HorizontalAlignment.Right, VerticalAlignment.Bottom, new Thickness(0, 0, -200, -220), .32));
        var layout = new Grid { Margin = new Thickness(26, 24, 26, 18) };
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.RowDefinitions.Add(new RowDefinition());
        layout.Children.Add(BuildSearch());
        caption.FontSize = 12; caption.Foreground = Brush("#8E8E93"); caption.Margin = new Thickness(6, 18, 0, 8); caption.Text = catalog == null ? "Завантаження програм…" : "Усі програми";
        Grid.SetRow(caption, 1); layout.Children.Add(caption);
        scroller.Style = (Style)Application.Current.FindResource("InkScrollViewer");
        scroller.VerticalScrollBarVisibility = ScrollBarVisibility.Auto; scroller.HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled;
        scroller.Content = grid; Grid.SetRow(scroller, 2); layout.Children.Add(scroller);
        content.Children.Add(layout);

        panel.Children.Add(shadow); panel.Children.Add(fill); panel.Children.Add(content); panel.Children.Add(rim);
        panel.RenderTransformOrigin = new Point(.5, .6);
        panel.RenderTransform = new TransformGroup { Children = { zoom, lift } };
        panel.Opacity = 0;
        return new Grid { Children = { panel } };
    }

    private static Ellipse Glow(Color color, HorizontalAlignment h, VerticalAlignment v, Thickness margin, double opacity) => new()
    {
        Width = 560, Height = 480, HorizontalAlignment = h, VerticalAlignment = v, Margin = margin, Opacity = opacity, IsHitTestVisible = false,
        Fill = new RadialGradientBrush(new GradientStopCollection { new(color, 0), new(Color.FromArgb(0, color.R, color.G, color.B), 1) }),
    };

    private UIElement BuildSearch()
    {
        var field = new Border { CornerRadius = new CornerRadius(16), Background = Brush("#E61C1C1E"), BorderBrush = Brush("#1FFFFFFF"), BorderThickness = new Thickness(1), Height = 52 };
        var row = new Grid();
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(48) }); row.ColumnDefinitions.Add(new ColumnDefinition());
        row.Children.Add(new TextBlock { Text = "", FontFamily = new FontFamily("Segoe Fluent Icons, Segoe MDL2 Assets"), FontSize = 17, Foreground = Brush("#8E8E93"), HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center });
        // A bare template keeps the field chrome ours (no Windows focus ring); the caret and selection stay native.
        search.Template = (ControlTemplate)XamlReader.Parse("""
            <ControlTemplate TargetType="TextBox" xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
              <ScrollViewer x:Name="PART_ContentHost" Focusable="False" VerticalAlignment="Center"/>
            </ControlTemplate>
            """);
        search.FontSize = 19; search.FontFamily = new FontFamily("Segoe UI Variable Display, Segoe UI"); search.Foreground = Brushes.White; search.CaretBrush = Brushes.White;
        search.Background = Brushes.Transparent; search.SelectionBrush = Brush("#0A84FF"); search.VerticalAlignment = VerticalAlignment.Center; search.Margin = new Thickness(0, 0, 16, 0);
        search.TextChanged += (_, _) => { placeholder.Visibility = search.Text.Length == 0 ? Visibility.Visible : Visibility.Collapsed; Filter(); };
        placeholder.Text = "Пошук програм"; placeholder.FontSize = 19; placeholder.FontFamily = search.FontFamily; placeholder.Foreground = Brush("#636366");
        placeholder.IsHitTestVisible = false; placeholder.VerticalAlignment = VerticalAlignment.Center; placeholder.Margin = new Thickness(2, 0, 0, 0);
        Grid.SetColumn(search, 1); Grid.SetColumn(placeholder, 1);
        row.Children.Add(placeholder); row.Children.Add(search);
        field.Child = row;
        return field;
    }

    private async Task Populate()
    {
        try
        {
            catalog ??= await (loading ??= LoadCatalog());
            // Let the entrance animation start before any tiles are built.
            await System.Windows.Threading.Dispatcher.Yield(System.Windows.Threading.DispatcherPriority.Background);
            Filter();
        }
        catch (Exception error) { Log.Error("launchpad catalog", error); caption.Text = "Не вдалося прочитати список програм"; }
    }

    private (Button Tile, Image Image, Border Placeholder) TileFor(LaunchApp app)
    {
        if (!tiles.TryGetValue(app, out var tile)) tiles[app] = tile = BuildTile(app);
        return tile;
    }

    private (Button, Image, Border) BuildTile(LaunchApp app)
    {
        var image = new Image { Width = 56, Height = 56, Source = app.Icon };
        RenderOptions.SetBitmapScalingMode(image, BitmapScalingMode.HighQuality);
        var placeholderIcon = new Border { Width = 56, Height = 56, CornerRadius = new CornerRadius(14), Background = Brush("#2C2C2E"), Visibility = app.Icon == null ? Visibility.Visible : Visibility.Collapsed };
        var label = new TextBlock { Text = app.Name, FontSize = 12, Foreground = Brush("#E5E5EA"), TextAlignment = TextAlignment.Center, TextWrapping = TextWrapping.Wrap, TextTrimming = TextTrimming.CharacterEllipsis, MaxHeight = 32, Width = 100, Margin = new Thickness(0, 8, 0, 0) };
        var stack = new StackPanel { HorizontalAlignment = HorizontalAlignment.Center };
        stack.Children.Add(new Grid { Children = { placeholderIcon, image } }); stack.Children.Add(label);
        var tile = new Button { Content = stack, Template = TileTemplate, Background = Brushes.Transparent, ToolTip = app.Name, Margin = new Thickness(3), Focusable = false };
        tile.Click += (_, _) => Launch(app);
        return (tile, image, placeholderIcon);
    }

    private static readonly ControlTemplate TileTemplate = (ControlTemplate)XamlReader.Parse("""
        <ControlTemplate TargetType="Button" xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
          <Border x:Name="Chrome" Background="{TemplateBinding Background}" CornerRadius="18" Padding="4,10,4,6"><ContentPresenter HorizontalAlignment="Center"/></Border>
          <ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="Chrome" Property="Background" Value="#17FFFFFF"/></Trigger></ControlTemplate.Triggers>
        </ControlTemplate>
        """);

    private int filterVersion;
    /// <summary>Shows matching apps; tiles are created on demand and added in small batches so typing and the
    /// entrance animation never stall on a few hundred icons.</summary>
    private async void Filter()
    {
        if (catalog == null) return;
        int version = ++filterVersion;
        string query = search.Text.Trim();
        visible = query.Length == 0 ? catalog : catalog
            .Where(a => a.Name.Contains(query, StringComparison.CurrentCultureIgnoreCase))
            .OrderBy(a => a.Name.StartsWith(query, StringComparison.CurrentCultureIgnoreCase) ? 0 : 1).ThenBy(a => a.Name, StringComparer.CurrentCultureIgnoreCase).ToList();
        grid.Children.Clear(); selected = 0;
        caption.Text = query.Length == 0 ? $"Усі програми · {catalog.Count}" : visible.Count == 0 ? "Нічого не знайдено" : $"Знайдено · {visible.Count}";
        scroller.ScrollToTop();
        var shown = visible;
        for (int i = 0; i < shown.Count; i++)
        {
            if (i > 0 && i % 24 == 0)
            {
                if (i == 24) Select(0);
                await System.Windows.Threading.Dispatcher.Yield(System.Windows.Threading.DispatcherPriority.Background);
                if (version != filterVersion) return;
            }
            grid.Children.Add(TileFor(shown[i]).Tile);
        }
        if (shown.Count <= 24) Select(0);
    }

    private void Select(int index)
    {
        if (visible.Count == 0) { selected = 0; return; }
        if (selected < visible.Count) TileFor(visible[selected]).Tile.Background = Brushes.Transparent;
        selected = Math.Clamp(index, 0, visible.Count - 1);
        // Only highlight while searching or navigating, like Spotlight's top hit.
        if (search.Text.Length > 0 || index != 0) { var tile = TileFor(visible[selected]).Tile; tile.Background = Brush("#330A84FF"); tile.BringIntoView(); }
    }

    private void OnKey(object sender, KeyEventArgs e)
    {
        switch (e.Key)
        {
            case Key.Escape: if (search.Text.Length > 0) search.Clear(); else Dismiss(); e.Handled = true; break;
            case Key.Enter: if (visible.Count > 0) Launch(visible[selected]); e.Handled = true; break;
            case Key.Right: if (search.CaretIndex == search.Text.Length) { Select(selected + 1); e.Handled = true; } break;
            case Key.Left: if (search.CaretIndex == search.Text.Length && search.Text.Length == 0) { Select(selected - 1); e.Handled = true; } break;
            case Key.Down: Select(selected + (int)Columns); e.Handled = true; break;
            case Key.Up: Select(selected - (int)Columns); e.Handled = true; break;
        }
    }

    private void OnIconLoaded(LaunchApp app)
    {
        if (!tiles.TryGetValue(app, out var tile)) return;
        tile.Image.Source = app.Icon; tile.Placeholder.Visibility = app.Icon == null ? Visibility.Visible : Visibility.Collapsed;
    }

    private void Launch(LaunchApp app)
    {
        try { Process.Start(new ProcessStartInfo("explorer.exe", "shell:AppsFolder\\" + app.ParsingName) { UseShellExecute = true }); }
        catch (Exception error) { Log.Error("launchpad launch", error); }
        Dismiss();
    }

    private void Appear()
    {
        var spring = new SpringEase { Damping = .72 };
        var duration = TimeSpan.FromMilliseconds(460);
        zoom.BeginAnimation(ScaleTransform.ScaleXProperty, new DoubleAnimation(.94, 1, duration) { EasingFunction = spring });
        zoom.BeginAnimation(ScaleTransform.ScaleYProperty, new DoubleAnimation(.94, 1, duration) { EasingFunction = spring });
        lift.BeginAnimation(TranslateTransform.YProperty, new DoubleAnimation(14, 0, duration) { EasingFunction = spring });
        panel.BeginAnimation(OpacityProperty, new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(170)));
    }

    public void Dismiss()
    {
        if (closing) return; closing = true;
        var duration = TimeSpan.FromMilliseconds(150); var ease = new CubicEase { EasingMode = EasingMode.EaseIn };
        zoom.BeginAnimation(ScaleTransform.ScaleXProperty, new DoubleAnimation(.96, duration) { EasingFunction = ease });
        zoom.BeginAnimation(ScaleTransform.ScaleYProperty, new DoubleAnimation(.96, duration) { EasingFunction = ease });
        var fade = new DoubleAnimation(0, duration) { EasingFunction = ease };
        fade.Completed += (_, _) => Close();
        panel.BeginAnimation(OpacityProperty, fade);
    }

    private static SolidColorBrush Brush(string value) { var brush = (SolidColorBrush)new BrushConverter().ConvertFromString(value)!; brush.Freeze(); return brush; }

    // ---- Catalog: every entry of shell:AppsFolder (the list Start shows under "Усі"), icons loaded progressively. ----

    private static readonly string[] Noise = ["uninstall", "видалити", "деінстал", "readme", "release notes", "documentation"];

    private static Task<List<LaunchApp>> LoadCatalog() => RunSta(() =>
    {
        var shellType = Type.GetTypeFromProgID("Shell.Application") ?? throw new InvalidOperationException("Shell.Application is unavailable");
        dynamic shell = Activator.CreateInstance(shellType)!;
        dynamic items = shell.NameSpace("shell:AppsFolder").Items();
        var apps = new List<LaunchApp>();
        int count = items.Count;
        for (int i = 0; i < count; i++)
        {
            dynamic item = items.Item(i);
            string name = item.Name, path = item.Path;
            if (string.IsNullOrWhiteSpace(name) || string.IsNullOrWhiteSpace(path) || Noise.Any(n => name.Contains(n, StringComparison.OrdinalIgnoreCase))) continue;
            apps.Add(new LaunchApp(name, path));
        }
        var result = apps.GroupBy(a => a.Name, StringComparer.CurrentCultureIgnoreCase).Select(g => g.First()).OrderBy(a => a.Name, StringComparer.CurrentCultureIgnoreCase).ToList();
        StartIconLoading(result);
        return result;
    });

    private static void StartIconLoading(List<LaunchApp> apps)
    {
        var dispatcher = Application.Current.Dispatcher;
        var thread = new Thread(() =>
        {
            foreach (var app in apps)
            {
                app.Icon = ShellIcon.Load("shell:AppsFolder\\" + app.ParsingName, 96);
                if (app.Icon != null) dispatcher.BeginInvoke(() => IconLoaded?.Invoke(app));
            }
        }) { IsBackground = true, Name = "Launchpad icons" };
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
    }

    private static Task<T> RunSta<T>(Func<T> work)
    {
        var done = new TaskCompletionSource<T>();
        var thread = new Thread(() => { try { done.SetResult(work()); } catch (Exception error) { done.SetException(error); } }) { IsBackground = true };
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        return done.Task;
    }
}

/// <summary>Large, alpha-correct shell icons (works for Store apps too) via IShellItemImageFactory.</summary>
internal static class ShellIcon
{
    [StructLayout(LayoutKind.Sequential)] private struct NativeSize { public int Width, Height; }
    [ComImport, Guid("bcc18b79-ba16-442f-80c4-8a59c30c463b"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IShellItemImageFactory { [PreserveSig] int GetImage(NativeSize size, int flags, out IntPtr bitmap); }
    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    private static extern void SHCreateItemFromParsingName(string path, IntPtr context, [MarshalAs(UnmanagedType.LPStruct)] Guid riid, [MarshalAs(UnmanagedType.Interface)] out IShellItemImageFactory item);
    [StructLayout(LayoutKind.Sequential)] private struct NativeBitmap { public int Type, Width, Height, WidthBytes; public ushort Planes, BitsPixel; public IntPtr Bits; }
    [StructLayout(LayoutKind.Sequential)] private struct NativeBitmapInfoHeader { public uint Size; public int Width, Height; public ushort Planes, BitCount; public uint Compression, SizeImage; public int XPelsPerMeter, YPelsPerMeter; public uint ClrUsed, ClrImportant; }
    [StructLayout(LayoutKind.Sequential)] private struct NativeDibSection { public NativeBitmap Bitmap; public NativeBitmapInfoHeader Header; public uint Mask0, Mask1, Mask2; public IntPtr Section; public uint Offset; }
    [DllImport("gdi32.dll")] private static extern int GetObject(IntPtr handle, int size, out NativeDibSection section);
    [DllImport("gdi32.dll")] private static extern bool DeleteObject(IntPtr handle);

    public static ImageSource? Load(string parsingName, int size)
    {
        IntPtr handle = IntPtr.Zero; IShellItemImageFactory? factory = null;
        try
        {
            SHCreateItemFromParsingName(parsingName, IntPtr.Zero, typeof(IShellItemImageFactory).GUID, out factory);
            if (factory.GetImage(new NativeSize { Width = size, Height = size }, 0x4 /* SIIGBF_ICONONLY */, out handle) != 0 || handle == IntPtr.Zero) return null;
            if (GetObject(handle, Marshal.SizeOf<NativeDibSection>(), out var dib) == 0 || dib.Bitmap.Bits == IntPtr.Zero || dib.Bitmap.BitsPixel != 32)
            {
                var opaque = Imaging.CreateBitmapSourceFromHBitmap(handle, IntPtr.Zero, Int32Rect.Empty, BitmapSizeOptions.FromEmptyOptions());
                opaque.Freeze(); return opaque;
            }
            int stride = dib.Bitmap.WidthBytes, height = dib.Bitmap.Height;
            BitmapSource source = BitmapSource.Create(dib.Bitmap.Width, height, 96, 96, PixelFormats.Pbgra32, null, dib.Bitmap.Bits, stride * height, stride);
            if (dib.Header.Height > 0) source = new TransformedBitmap(source, new ScaleTransform(1, -1)); // bottom-up DIB
            source.Freeze();
            return source;
        }
        catch { return null; }
        finally
        {
            if (handle != IntPtr.Zero) DeleteObject(handle);
            if (factory != null) Marshal.ReleaseComObject(factory);
        }
    }
}
