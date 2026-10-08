using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Net.NetworkInformation;
using System.Net.Sockets;
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
using System.IO;
using Path = System.Windows.Shapes.Path;

namespace Island.Windows;

/// <summary>
/// Top-panel flyouts (apps/search, quick access, calendar, network, keyboard language) drawn in the island's
/// language: a continuous-corner dark sheet with a light rim, soft shadow and spring entrance.
/// </summary>
public sealed class ShellPopup : Window
{
    private const double SheetWidth = 368, Pad = 18;
    private static readonly CultureInfo Ukrainian = CultureInfo.GetCultureInfo("uk-UA");
    private readonly StackPanel body = new() { Margin = new Thickness(18, 18, 18, 16) };
    private readonly Grid surface = new() { Width = SheetWidth };
    private readonly Path fill = new(), rim = new(), shadow = new();
    private readonly Grid content = new();
    private readonly ScaleTransform zoom = new(.96, .96);
    private readonly TranslateTransform drop = new(0, -8);
    private readonly IntPtr previousWindow;
    private bool closing;
    public string Kind { get; }

    public ShellPopup(string kind, IEnumerable<ShellApp> running, IntPtr target)
    {
        Kind = kind; previousWindow = target;
        Title = "Island · " + kind; Width = SheetWidth + Pad * 2; SizeToContent = SizeToContent.Height; MaxHeight = 660;
        WindowStyle = WindowStyle.None; AllowsTransparency = true; Background = Brushes.Transparent; Topmost = true;
        ShowInTaskbar = false; ResizeMode = ResizeMode.NoResize; UseLayoutRounding = true;
        Content = BuildChrome();
        SourceInitialized += (_, _) => ShellNative.ToolWindow(new WindowInteropHelper(this).Handle);
        Closing += (_, _) => closing = true;
        Deactivated += (_, _) => { if (!closing) Close(); };
        PreviewKeyDown += (_, e) => { if (e.Key == Key.Escape) { Close(); e.Handled = true; } };
        Loaded += (_, _) => Appear();
        if (kind is "apps" or "search" or "tray") Apps(running, kind == "tray");
        else if (kind == "calendar") Calendar(DateTime.Today);
        else if (kind == "network") Network();
        else if (kind == "language") Languages();
    }

    private UIElement BuildChrome()
    {
        shadow.Fill = Brushes.Black; shadow.Opacity = .5; shadow.IsHitTestVisible = false; shadow.Effect = new BlurEffect { Radius = 22 }; shadow.RenderTransform = new TranslateTransform(0, 8);
        fill.Fill = new LinearGradientBrush(Color.FromRgb(0x18, 0x18, 0x1B), Color.FromRgb(0x0D, 0x0D, 0x0F), 90);
        rim.StrokeThickness = 1; rim.IsHitTestVisible = false;
        rim.Stroke = new LinearGradientBrush(new GradientStopCollection { new(Color.FromArgb(0x40, 255, 255, 255), 0), new(Color.FromArgb(0x10, 255, 255, 255), .3), new(Color.FromArgb(0x06, 255, 255, 255), 1) }, 90);
        var glow = new Ellipse { Width = 420, Height = 340, HorizontalAlignment = HorizontalAlignment.Left, VerticalAlignment = VerticalAlignment.Top, Margin = new Thickness(-170, -190, 0, 0), Opacity = .38, IsHitTestVisible = false,
            Fill = new RadialGradientBrush(new GradientStopCollection { new(Color.FromRgb(0x3A, 0x5A, 0xD0), 0), new(Color.FromArgb(0, 0x3A, 0x5A, 0xD0), 1) }) };
        var scroller = new ScrollViewer { Content = body, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, MaxHeight = 620, Style = (Style)Application.Current.FindResource("InkScrollViewer") };
        content.Children.Add(glow); content.Children.Add(scroller);
        surface.Children.Add(shadow); surface.Children.Add(fill); surface.Children.Add(content); surface.Children.Add(rim);
        surface.SizeChanged += (_, e) =>
        {
            var outline = IslandModel.Squircle(e.NewSize.Width, e.NewSize.Height, 26);
            shadow.Data = fill.Data = rim.Data = outline; content.Clip = outline;
        };
        surface.RenderTransformOrigin = new Point(.5, 0);
        surface.RenderTransform = new TransformGroup { Children = { zoom, drop } };
        surface.Opacity = 0;
        return new Grid { Margin = new Thickness(Pad, 6, Pad, Pad + 10), Children = { surface } };
    }

    private void Appear()
    {
        var spring = new SpringEase { Damping = .72 }; var duration = TimeSpan.FromMilliseconds(420);
        zoom.BeginAnimation(ScaleTransform.ScaleXProperty, new DoubleAnimation(.96, 1, duration) { EasingFunction = spring });
        zoom.BeginAnimation(ScaleTransform.ScaleYProperty, new DoubleAnimation(.96, 1, duration) { EasingFunction = spring });
        drop.BeginAnimation(TranslateTransform.YProperty, new DoubleAnimation(-8, 0, duration) { EasingFunction = spring });
        surface.BeginAnimation(OpacityProperty, new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(150)));
    }

    // ---- Building blocks ----

    private static SolidColorBrush Hex(string value) { var brush = (SolidColorBrush)new BrushConverter().ConvertFromString(value)!; brush.Freeze(); return brush; }
    private static readonly FontFamily Display = new("Segoe UI Variable Display, Segoe UI"), Icons = new("Segoe Fluent Icons, Segoe MDL2 Assets");
    private static TextBlock Glyph(string glyph, double size, string color = "#FFFFFF") => new() { Text = glyph, FontFamily = Icons, FontSize = size, Foreground = Hex(color), HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center };
    private static Grid Disc(string glyph, string color, double size = 34) => new() { Width = size, Height = size, Children = { new Ellipse { Fill = Hex(color) }, Glyph(glyph, size * .44) } };

    private void Heading(string title, string subtitle, UIElement? accessory = null)
    {
        var row = new Grid { Margin = new Thickness(4, 0, 0, 14) };
        var text = new StackPanel();
        text.Children.Add(new TextBlock { Text = title, FontFamily = Display, FontSize = 20, FontWeight = FontWeights.SemiBold });
        if (subtitle.Length > 0) text.Children.Add(new TextBlock { Text = subtitle, FontSize = 12, Foreground = Hex("#8E8E93"), Margin = new Thickness(0, 2, 0, 0), TextWrapping = TextWrapping.Wrap });
        row.Children.Add(text);
        if (accessory is FrameworkElement element) { element.HorizontalAlignment = HorizontalAlignment.Right; element.VerticalAlignment = VerticalAlignment.Center; row.Children.Add(element); }
        body.Children.Add(row);
    }

    private static readonly ControlTemplate RowTemplate = (ControlTemplate)XamlReader.Parse("""
        <ControlTemplate TargetType="Button" xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
          <Border x:Name="Chrome" Background="{TemplateBinding Background}" CornerRadius="12" Padding="{TemplateBinding Padding}"><ContentPresenter HorizontalAlignment="Stretch" VerticalAlignment="Center"/></Border>
          <ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="Chrome" Property="Background" Value="#1AFFFFFF"/></Trigger></ControlTemplate.Triggers>
        </ControlTemplate>
        """);

    /// <summary>A tappable list row: leading visual, title + subtitle, optional trailing text.</summary>
    private static Button Row(UIElement? leading, string title, string subtitle, Action action, string trailing = "")
    {
        var grid = new Grid();
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto }); grid.ColumnDefinitions.Add(new ColumnDefinition()); grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        if (leading is FrameworkElement lead) { lead.Margin = new Thickness(0, 0, 12, 0); grid.Children.Add(lead); }
        var text = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
        text.Children.Add(new TextBlock { Text = title, FontSize = 13, FontWeight = FontWeights.SemiBold, TextTrimming = TextTrimming.CharacterEllipsis });
        if (subtitle.Length > 0) text.Children.Add(new TextBlock { Text = subtitle, FontSize = 11, Foreground = Hex("#8E8E93"), TextTrimming = TextTrimming.CharacterEllipsis, Margin = new Thickness(0, 1, 0, 0) });
        Grid.SetColumn(text, 1); grid.Children.Add(text);
        if (trailing.Length > 0) { var tail = new TextBlock { Text = trailing, FontSize = 12, Foreground = Hex("#8E8E93"), VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(10, 0, 0, 0) }; Grid.SetColumn(tail, 2); grid.Children.Add(tail); }
        var button = new Button { Content = grid, Template = RowTemplate, Background = Brushes.Transparent, Padding = new Thickness(10, 8, 10, 8), HorizontalContentAlignment = HorizontalAlignment.Stretch, Focusable = false };
        button.Click += (_, _) => action();
        return button;
    }

    /// <summary>iOS inset group: a raised module whose rows are separated by hairlines.</summary>
    private void Group(IEnumerable<UIElement> rows, string header = "")
    {
        if (header.Length > 0) body.Children.Add(new TextBlock { Text = header, FontSize = 12, FontWeight = FontWeights.SemiBold, Foreground = Hex("#8E8E93"), Margin = new Thickness(6, 4, 0, 6) });
        var stack = new StackPanel(); bool first = true;
        foreach (var row in rows)
        {
            if (!first) stack.Children.Add(new Border { Height = 1, Background = Hex("#2A2A2D"), Margin = new Thickness(54, 0, 10, 0) });
            stack.Children.Add(row); first = false;
        }
        body.Children.Add(new Border { Style = (Style)Application.Current.FindResource("Group"), Padding = new Thickness(4), Margin = new Thickness(0, 0, 0, 12), Child = stack });
    }

    private static Button Chip(string text, Action action, bool accent = false)
    {
        var chip = new Button { Style = (Style)Application.Current.FindResource("Chip"), Content = text, Margin = new Thickness(0, 0, 8, 0) };
        if (accent) chip.Background = Hex("#0A84FF");
        chip.Click += (_, _) => action(); return chip;
    }

    private static Button Round(string glyph, Action action)
    {
        var button = new Button { Style = (Style)Application.Current.FindResource("Round"), Width = 32, Height = 32, Background = Hex("#2C2C2E"), Content = Glyph(glyph, 11), Margin = new Thickness(6, 0, 0, 0) };
        button.Click += (_, _) => action(); return button;
    }

    private static TextBox SearchField(string hint, out UIElement field)
    {
        var box = new TextBox
        {
            Template = (ControlTemplate)XamlReader.Parse("""
                <ControlTemplate TargetType="TextBox" xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
                  <ScrollViewer x:Name="PART_ContentHost" Focusable="False" VerticalAlignment="Center"/>
                </ControlTemplate>
                """),
            FontSize = 15, Foreground = Brushes.White, CaretBrush = Brushes.White, Background = Brushes.Transparent, SelectionBrush = Hex("#0A84FF"), VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 12, 0),
        };
        var placeholder = new TextBlock { Text = hint, FontSize = 15, Foreground = Hex("#636366"), IsHitTestVisible = false, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(2, 0, 0, 0) };
        box.TextChanged += (_, _) => placeholder.Visibility = box.Text.Length == 0 ? Visibility.Visible : Visibility.Collapsed;
        var grid = new Grid();
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(40) }); grid.ColumnDefinitions.Add(new ColumnDefinition());
        grid.Children.Add(Glyph("", 14, "#8E8E93"));
        Grid.SetColumn(placeholder, 1); Grid.SetColumn(box, 1); grid.Children.Add(placeholder); grid.Children.Add(box);
        field = new Border { CornerRadius = new CornerRadius(14), Background = Hex("#1C1C1E"), BorderBrush = Hex("#1FFFFFFF"), BorderThickness = new Thickness(1), Height = 44, Margin = new Thickness(0, 0, 0, 12), Child = grid };
        return box;
    }

    // ---- Views ----

    private void Apps(IEnumerable<ShellApp> running, bool tray)
    {
        Heading(tray ? "Швидкий доступ" : "Відкриті вікна", tray ? "Маленькі помічники у верхній панелі" : "Перемкнися або знайди потрібне вікно");
        var source = running.Where(a => !tray || a.TopBarOnly).ToArray();
        TextBox? search = null;
        if (!tray) { search = SearchField("Пошук вікон", out var field); body.Children.Add(field); }
        var list = new StackPanel();
        body.Children.Add(new Border { Style = (Style)Application.Current.FindResource("Group"), Padding = new Thickness(4), Margin = new Thickness(0, 0, 0, 12), Child = list });
        ShellApp[] shown = [];
        void Render()
        {
            list.Children.Clear();
            string query = search?.Text ?? "";
            shown = source.Where(a => (a.Name + " " + a.Title).Contains(query, StringComparison.CurrentCultureIgnoreCase)).ToArray();
            foreach (var app in shown)
            {
                UIElement icon = app.Icon != null ? new Image { Source = app.Icon, Width = 30, Height = 30 } : Disc("", "#3A3A3C", 30);
                list.Children.Add(Row(icon, app.Name, app.Title, () => { Close(); ShellNative.Switch(app.Handle); }));
            }
            if (shown.Length == 0) list.Children.Add(new TextBlock { Text = "Нічого не знайдено", Foreground = Hex("#8E8E93"), Margin = new Thickness(12, 10, 12, 10) });
        }
        if (search != null)
        {
            search.TextChanged += (_, _) => Render();
            search.PreviewKeyDown += (_, e) => { if (e.Key == Key.Enter && shown.Length > 0) { Close(); ShellNative.Switch(shown[0].Handle); e.Handled = true; } };
            Loaded += (_, _) => search.Focus();
        }
        Render();
        if (!tray)
        {
            var chips = new WrapPanel { Margin = new Thickness(2, 0, 0, 2) };
            chips.Children.Add(Chip("Усі програми", () => { Close(); Launchpad.Toggle(); }, accent: true));
            chips.Children.Add(Chip("Файли", () => { Close(); DesktopService.Open("explorer.exe"); }));
            body.Children.Add(chips);
        }
    }

    private void Calendar(DateTime month)
    {
        body.Children.Clear();
        var arrows = new StackPanel { Orientation = Orientation.Horizontal };
        arrows.Children.Add(Round("", () => Calendar(month.AddMonths(-1))));
        arrows.Children.Add(Round("", () => Calendar(month.AddMonths(1))));
        var title = month.ToString("MMMM yyyy", Ukrainian);
        var today = DateTime.Today.ToString("dddd, d MMMM", Ukrainian);
        Heading(char.ToUpper(title[0]) + title[1..], char.ToUpper(today[0]) + today[1..], arrows);

        var grid = new System.Windows.Controls.Primitives.UniformGrid { Columns = 7 };
        string[] names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"];
        for (int i = 0; i < 7; i++) grid.Children.Add(new TextBlock { Text = names[i], FontSize = 11, FontWeight = FontWeights.SemiBold, HorizontalAlignment = HorizontalAlignment.Center, Foreground = Hex(i >= 5 ? "#636366" : "#8E8E93"), Margin = new Thickness(0, 0, 0, 8) });
        var first = new DateTime(month.Year, month.Month, 1); int offset = ((int)first.DayOfWeek + 6) % 7;
        for (int i = 0; i < offset; i++) grid.Children.Add(new Border());
        for (int n = 1; n <= DateTime.DaysInMonth(month.Year, month.Month); n++)
        {
            var day = new DateTime(month.Year, month.Month, n); bool isToday = day == DateTime.Today, weekend = day.DayOfWeek is DayOfWeek.Saturday or DayOfWeek.Sunday;
            grid.Children.Add(new Border
            {
                Width = 38, Height = 38, Margin = new Thickness(0, 1, 0, 1), CornerRadius = new CornerRadius(19), Background = isToday ? Hex("#0A84FF") : Brushes.Transparent,
                Child = new TextBlock { Text = n.ToString(), FontSize = 14, FontWeight = isToday ? FontWeights.SemiBold : FontWeights.Normal, Foreground = isToday ? Brushes.White : Hex(weekend ? "#8E8E93" : "#F2F2F7"), HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center },
            });
        }
        body.Children.Add(new Border { Style = (Style)Application.Current.FindResource("Group"), Padding = new Thickness(10, 14, 10, 10), Margin = new Thickness(0, 0, 0, 10), Child = grid });
        if (month.Year != DateTime.Today.Year || month.Month != DateTime.Today.Month)
            body.Children.Add(new WrapPanel { Margin = new Thickness(2, 0, 0, 2), Children = { Chip("Сьогодні", () => Calendar(DateTime.Today), accent: true) } });
    }

    // Driver plumbing (filter/miniport layers) is not a "network" to a person; hide it like macOS does.
    private static readonly string[] Plumbing = ["filter", "-0000", "wfp", "qos", "scheduler", "npcap", "miniport", "kernel debug", "teredo", "isatap", "pseudo"];

    private void Network()
    {
        var all = NetworkInterface.GetAllNetworkInterfaces()
            .Where(n => n.OperationalStatus == OperationalStatus.Up && n.NetworkInterfaceType != NetworkInterfaceType.Loopback)
            .Where(n => !Plumbing.Any(p => (n.Name + " " + n.Description).Contains(p, StringComparison.OrdinalIgnoreCase)))
            .Where(n => !System.Text.RegularExpressions.Regex.IsMatch(n.Name, @"-\d{4}$")).ToArray(); // "Ethernet--0003": per-filter clones
        bool Primary(NetworkInterface n) { try { return n.GetIPProperties().GatewayAddresses.Any(g => !g.Address.Equals(System.Net.IPAddress.Any)); } catch { return false; } }
        bool Virtual(NetworkInterface n) => (n.Name + " " + n.Description).Contains("vEthernet", StringComparison.OrdinalIgnoreCase) || (n.Name + " " + n.Description).Contains("Virtual", StringComparison.OrdinalIgnoreCase) || n.Description.Contains("VPN", StringComparison.OrdinalIgnoreCase);
        var main = all.FirstOrDefault(n => Primary(n) && !Virtual(n)) ?? all.FirstOrDefault(Primary);
        Heading("Мережа", NetworkInterface.GetIsNetworkAvailable() ? "Підключення активне" : "Немає активного підключення");

        if (main != null)
        {
            bool wifi = main.NetworkInterfaceType == NetworkInterfaceType.Wireless80211;
            var hero = new Grid();
            hero.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto }); hero.ColumnDefinitions.Add(new ColumnDefinition());
            hero.Children.Add(Disc(wifi ? "" : "", "#0A84FF", 44));
            var text = new StackPanel { Margin = new Thickness(12, 0, 0, 0), VerticalAlignment = VerticalAlignment.Center };
            text.Children.Add(new TextBlock { Text = wifi ? "Wi‑Fi" : "Ethernet", FontFamily = Display, FontSize = 16, FontWeight = FontWeights.SemiBold });
            text.Children.Add(new TextBlock { Text = $"Підключено · {Speed(main.Speed)}", FontSize = 12, Foreground = Hex("#30D158"), Margin = new Thickness(0, 2, 0, 0) });
            text.Children.Add(new TextBlock { Text = Address(main), FontSize = 11, Foreground = Hex("#8E8E93"), Margin = new Thickness(0, 2, 0, 0), TextTrimming = TextTrimming.CharacterEllipsis });
            Grid.SetColumn(text, 1); hero.Children.Add(text);
            body.Children.Add(new Border { Style = (Style)Application.Current.FindResource("Module"), Padding = new Thickness(14), Child = hero });
        }
        var others = all.Where(n => n != main).ToArray();
        var real = others.Where(n => !Virtual(n)).Select(n => (UIElement)AdapterRow(n)).ToList();
        var virtualAdapters = others.Where(Virtual).Select(n => (UIElement)AdapterRow(n)).ToList();
        if (real.Count > 0) Group(real, "Інші підключення");
        if (virtualAdapters.Count > 0) Group(virtualAdapters, "Віртуальні адаптери");
        body.Children.Add(new WrapPanel { Margin = new Thickness(2, 0, 0, 2), Children = { Chip("Налаштування мережі ↗", () => { Close(); DesktopService.Open("ms-settings:network"); }) } });
    }

    private Button AdapterRow(NetworkInterface net)
    {
        bool wifi = net.NetworkInterfaceType == NetworkInterfaceType.Wireless80211;
        return Row(Disc(wifi ? "" : "", "#3A3A3C", 30), net.Name, Address(net), () => { Close(); DesktopService.Open("ms-settings:network"); }, Speed(net.Speed));
    }

    private static string Speed(long bits) => bits <= 0 ? "" : bits >= 1_000_000_000 ? $"{bits / 1_000_000_000.0:0.#} Гбіт/с" : $"{bits / 1_000_000} Мбіт/с";
    private static string Address(NetworkInterface net)
    {
        try { return net.GetIPProperties().UnicastAddresses.FirstOrDefault(a => a.Address.AddressFamily == AddressFamily.InterNetwork)?.Address.ToString() ?? net.Description; }
        catch { return net.Description; }
    }

    private void Languages()
    {
        Heading("Мова клавіатури", "Застосовується до попереднього вікна");
        Group(ShellNative.Layouts().Select(layout =>
        {
            var captured = layout;
            string code = layout.Name.Length >= 2 ? layout.Name[..2].ToUpperInvariant() : layout.Name.ToUpperInvariant();
            var badge = new Border { Width = 34, Height = 26, CornerRadius = new CornerRadius(7), Background = Hex("#2C2C2E"), Child = new TextBlock { Text = code, FontSize = 11, FontWeight = FontWeights.SemiBold, HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center } };
            return (UIElement)Row(badge, layout.Name, "", () => { Close(); ShellNative.SetLayout(previousWindow, captured.Handle); });
        }));
    }

    public void Snapshot(string path)
    {
        UpdateLayout(); double scale = VisualTreeHelper.GetDpi(this).DpiScaleX;
        var bitmap = new RenderTargetBitmap((int)Math.Ceiling(surface.ActualWidth * scale), (int)Math.Ceiling(surface.ActualHeight * scale), 96 * scale, 96 * scale, PixelFormats.Pbgra32);
        var visual = new DrawingVisual(); using (var context = visual.RenderOpen()) context.DrawRectangle(new VisualBrush(surface), null, new Rect(0, 0, surface.ActualWidth, surface.ActualHeight));
        bitmap.Render(visual);
        var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(bitmap)); using var file = File.Create(path); png.Save(file);
    }
}
