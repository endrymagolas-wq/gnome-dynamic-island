using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
using Path = System.Windows.Shapes.Path;

namespace Island.Windows;

/// <summary>
/// Glass presentation for the bottom dock with stable icons and a restrained hover highlight.
/// </summary>
public static class DockStyle
{
    /// <summary>Transparent room under the slab so its shadow can fade out instead of being cut at the window edge.</summary>
    public const double BottomBleed = 12;
    private const double SlabHeight = 64, Headroom = 56, SideRoom = 44, IconScale = 1.2;

    public static void Apply(Window dock, Border surface, Panel apps)
    {
        // Keep a near-transparent dark brush: it stays hit-testable between icons and DesktopShell still reads it as a dark dock.
        surface.Background = new SolidColorBrush(Color.FromArgb(1, 0x1C, 0x1C, 0x1E));
        surface.BorderThickness = new Thickness(0); surface.CornerRadius = new CornerRadius(0);
        surface.Padding = new Thickness(10, 5, 10, 5); surface.Height = SlabHeight; surface.VerticalAlignment = VerticalAlignment.Bottom;
        apps.LayoutTransform = new ScaleTransform(IconScale, IconScale);
        apps.VerticalAlignment = VerticalAlignment.Center;
        RenderOptions.SetBitmapScalingMode(apps, BitmapScalingMode.HighQuality);

        var shadow = new Path { Fill = Brushes.Black, Opacity = .45, IsHitTestVisible = false, Effect = new BlurEffect { Radius = 18 }, RenderTransform = new TranslateTransform(0, 6), VerticalAlignment = VerticalAlignment.Bottom };
        var glass = new Path
        {
            IsHitTestVisible = false, VerticalAlignment = VerticalAlignment.Bottom,
            Fill = new LinearGradientBrush(new GradientStopCollection { new(Color.FromArgb(0xD8, 0x2A, 0x2A, 0x2E), 0), new(Color.FromArgb(0xD8, 0x18, 0x18, 0x1B), 1) }, 90),
        };
        var sheen = new Path
        {
            IsHitTestVisible = false, VerticalAlignment = VerticalAlignment.Bottom,
            Fill = new LinearGradientBrush(new GradientStopCollection { new(Color.FromArgb(0x22, 255, 255, 255), 0), new(Color.FromArgb(0x00, 255, 255, 255), .55) }, 90),
        };
        var rim = new Path
        {
            IsHitTestVisible = false, VerticalAlignment = VerticalAlignment.Bottom, StrokeThickness = 1,
            Stroke = new LinearGradientBrush(new GradientStopCollection { new(Color.FromArgb(0x55, 255, 255, 255), 0), new(Color.FromArgb(0x18, 255, 255, 255), .4), new(Color.FromArgb(0x10, 255, 255, 255), 1) }, 90),
        };
        var slab = new[] { shadow, glass, sheen, rim };
        void Reshape()
        {
            double width = surface.ActualWidth, height = surface.ActualHeight;
            if (width <= 0 || height <= 0) return;
            var outline = IslandModel.Squircle(width, height, 22);
            // The slab paths live on Canvases, which never take part in layout: the dock's width comes from the icons
            // alone (an explicit path width used to keep the window wide after an app left the dock).
            foreach (var path in slab) { path.Data = outline; path.Width = width; path.Height = height; }
        }
        surface.SizeChanged += (_, _) => Reshape();

        dock.Content = null;
        var stage = new Grid { Margin = new Thickness(SideRoom, 0, SideRoom, BottomBleed) };
        Canvas Layer(params Path[] paths) { var layer = new Canvas { Height = SlabHeight, VerticalAlignment = VerticalAlignment.Bottom, IsHitTestVisible = false }; foreach (var path in paths) layer.Children.Add(path); return layer; }
        stage.Children.Add(Layer(shadow, glass, sheen)); stage.Children.Add(surface); stage.Children.Add(Layer(rim));
        dock.Content = stage;
        dock.Height = SlabHeight + Headroom + BottomBleed;
    }

    private static readonly ControlTemplate PlainButton = (ControlTemplate)System.Windows.Markup.XamlReader.Parse(
        "<ControlTemplate TargetType=\"Button\" xmlns=\"http://schemas.microsoft.com/winfx/2006/xaml/presentation\"><Border Background=\"#01000000\" Padding=\"{TemplateBinding Padding}\"><Grid><Border x:Name=\"Highlight\" xmlns:x=\"http://schemas.microsoft.com/winfx/2006/xaml\" Background=\"White\" CornerRadius=\"9\" Opacity=\"0\"/><ContentPresenter HorizontalAlignment=\"Center\" VerticalAlignment=\"Center\"/></Grid></Border><ControlTemplate.Triggers><Trigger Property=\"IsEnabled\" Value=\"False\"><Setter Property=\"Opacity\" Value=\"0.3\"/></Trigger></ControlTemplate.Triggers></ControlTemplate>");

    /// <summary>Applied to every rebuilt dock button; no icon transform or rendering-loop subscription.</summary>
    public static void ConfigureButton(Button button, Func<bool> animations)
    {
        button.Template = PlainButton;
        button.RenderTransform = Transform.Identity;
        ToolTipService.SetPlacement(button, PlacementMode.Top);
        ToolTipService.SetVerticalOffset(button, -6);
        ToolTipService.SetInitialShowDelay(button, 350);
        void Highlight(double opacity, int milliseconds = 100)
        {
            button.ApplyTemplate();
            if (button.Template.FindName("Highlight", button) is not Border glow) return;
            double from = glow.Opacity;
            glow.BeginAnimation(UIElement.OpacityProperty, null);
            glow.Opacity = opacity;
            if (animations()) glow.BeginAnimation(UIElement.OpacityProperty,
                new DoubleAnimation(from, opacity, TimeSpan.FromMilliseconds(milliseconds))
                { EasingFunction = new QuadraticEase { EasingMode = EasingMode.EaseOut }, FillBehavior = FillBehavior.Stop });
        }
        button.MouseEnter += (_, _) => Highlight(.08);
        button.MouseLeave += (_, _) => Highlight(0);
        button.PreviewMouseLeftButtonDown += (_, _) => Highlight(.14, 50);
        button.PreviewMouseLeftButtonUp += (_, _) => Highlight(button.IsMouseOver ? .08 : 0);
        button.LostMouseCapture += (_, _) => Highlight(button.IsMouseOver ? .08 : 0);
    }
}
