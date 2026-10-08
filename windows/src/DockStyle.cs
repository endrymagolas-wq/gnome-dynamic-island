using System;
using System.Collections.Generic;
using System.Linq;
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
/// macOS-style presentation for the bottom dock, layered on top of DesktopShell's dock without touching its logic:
/// a continuous-corner glass slab (sheen, rim, shadow), slightly larger icons, the magnification wave that follows
/// the pointer and spreads neighbours apart, and the launch bounce.
/// </summary>
public static class DockStyle
{
    /// <summary>Transparent room under the slab so its shadow can fade out instead of being cut at the window edge.</summary>
    public const double BottomBleed = 12;
    private const double SlabHeight = 64, Headroom = 56, SideRoom = 44, MaxScale = 1.45, Spread = 1.05, IconScale = 1.2;

    public static void Apply(Window dock, Border surface, Panel apps, Func<bool> animations)
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
        // The glass widens with the magnification wave (like macOS) so edge icons never hang off the slab.
        void Reshape(double grow)
        {
            double width = surface.ActualWidth + grow, height = surface.ActualHeight;
            if (width <= 0 || height <= 0) return;
            var outline = IslandModel.Squircle(width, height, 22);
            // The slab paths live on Canvases, which never take part in layout: the dock's width comes from the icons
            // alone (an explicit path width used to keep the window wide after an app left the dock).
            foreach (var path in slab) { path.Data = outline; path.Width = width; path.Height = height; Canvas.SetLeft(path, -grow / 2); }
        }
        surface.SizeChanged += (_, _) => Reshape(0);

        dock.Content = null;
        var stage = new Grid { Margin = new Thickness(SideRoom, 0, SideRoom, BottomBleed) };
        Canvas Layer(params Path[] paths) { var layer = new Canvas { Height = SlabHeight, VerticalAlignment = VerticalAlignment.Bottom, IsHitTestVisible = false }; foreach (var path in paths) layer.Children.Add(path); return layer; }
        stage.Children.Add(Layer(shadow, glass, sheen)); stage.Children.Add(surface); stage.Children.Add(Layer(rim));
        dock.Content = stage;
        dock.Height = SlabHeight + Headroom + BottomBleed; // the extra height above the slab is transparent (click-through) room for magnified icons

        new Magnifier(apps, animations, Reshape).Attach();
    }

    private static readonly ControlTemplate PlainButton = (ControlTemplate)System.Windows.Markup.XamlReader.Parse(
        "<ControlTemplate TargetType=\"Button\" xmlns=\"http://schemas.microsoft.com/winfx/2006/xaml/presentation\"><Border Background=\"#01000000\" Padding=\"{TemplateBinding Padding}\"><ContentPresenter HorizontalAlignment=\"Center\" VerticalAlignment=\"Center\"/></Border></ControlTemplate>");

    /// <summary>Per-frame magnification wave with easing in and out, plus the click bounce.</summary>
    private sealed class Magnifier(Panel apps, Func<bool> animations, Action<double> reshape)
    {
        private readonly Dictionary<UIElement, double> scale = new();
        private double? pointer;
        private double grown;
        private bool running;

        public void Attach()
        {
            apps.MouseMove += (_, e) => { pointer = e.GetPosition(apps).X; Start(); };
            apps.MouseLeave += (_, _) => { pointer = null; Start(); };
            apps.AddHandler(ButtonBase.ClickEvent, new RoutedEventHandler((_, e) => { if (e.OriginalSource is Button button) Bounce(button); }));
        }

        private void Start() { if (running) return; running = true; CompositionTarget.Rendering += Frame; }

        private static (ScaleTransform Scale, TranslateTransform Shift) Transforms(UIElement item)
        {
            if (item.RenderTransform is TransformGroup group && group.Children.Count == 3 && group.Children[0] is ScaleTransform s && group.Children[1] is TranslateTransform t)
                return (s, t);
            // macOS shows no hover plate behind dock icons; magnification is the only hover feedback.
            if (item is Button button)
            {
                button.Template = PlainButton;
                // macOS shows the app name above the (magnified) icon, never on top of the row.
                ToolTipService.SetPlacement(button, PlacementMode.Top);
                ToolTipService.SetVerticalOffset(button, -26);
                ToolTipService.SetInitialShowDelay(button, 250);
            }
            var scale = item.RenderTransform as ScaleTransform ?? new ScaleTransform();
            var shift = new TranslateTransform(); var bounce = new TranslateTransform();
            item.RenderTransformOrigin = new Point(.5, 1);
            item.RenderTransform = new TransformGroup { Children = { scale, shift, bounce } };
            return (scale, shift);
        }

        private void Frame(object? sender, EventArgs e)
        {
            var items = apps.Children.OfType<UIElement>().Where(i => i.Visibility == Visibility.Visible).ToList();
            if (items.Count == 0) { Stop(); return; }
            bool animate = animations();
            double pitch = items.Average(i => i.RenderSize.Width);
            var centers = new List<double>(); double x = 0;
            foreach (var item in items) { centers.Add(x + item.RenderSize.Width / 2); x += item.RenderSize.Width; }

            bool settled = true;
            var current = new double[items.Count];
            for (int i = 0; i < items.Count; i++)
            {
                double target = 1;
                if (pointer is double px)
                {
                    double d = (px - centers[i]) / Math.Max(1, pitch);
                    target = 1 + (MaxScale - 1) * Math.Exp(-d * d / (2 * Spread * Spread));
                }
                double now = scale.TryGetValue(items[i], out var s) ? s : 1;
                double next = animate ? now + (target - now) * .28 : target;
                if (Math.Abs(next - target) < .002) next = target; else settled = false;
                scale[items[i]] = next; current[i] = next;
            }
            // Spread neighbours so magnified icons push each other aside, and stretch the glass by the same amount.
            double stretch = 0;
            for (int i = 0; i < items.Count; i++) stretch += (current[i] - 1) * items[i].RenderSize.Width;
            stretch *= .6 * IconScale;
            if (Math.Abs(stretch - grown) > .3 || (stretch == 0 && grown != 0)) { grown = stretch; reshape(stretch); }
            for (int i = 0; i < items.Count; i++)
            {
                var (s, t) = Transforms(items[i]);
                s.ScaleX = s.ScaleY = current[i];
                double push = 0;
                for (int j = 0; j < items.Count; j++)
                {
                    double extra = (current[j] - 1) * items[j].RenderSize.Width;
                    if (j < i) push += extra / 2; else if (j > i) push -= extra / 2;
                }
                t.X = push * .6;
            }
            if (settled && pointer == null) Stop();
        }

        private void Stop() { if (!running) return; running = false; CompositionTarget.Rendering -= Frame; }

        private void Bounce(Button button)
        {
            if (!animations()) return;
            Transforms(button);
            if (button.RenderTransform is not TransformGroup group || group.Children[2] is not TranslateTransform hop) return;
            var jump = new DoubleAnimationUsingKeyFrames { Duration = TimeSpan.FromMilliseconds(900) };
            jump.KeyFrames.Add(new EasingDoubleKeyFrame(-18, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(180)), new QuadraticEase { EasingMode = EasingMode.EaseOut }));
            jump.KeyFrames.Add(new EasingDoubleKeyFrame(0, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(360)), new QuadraticEase { EasingMode = EasingMode.EaseIn }));
            jump.KeyFrames.Add(new EasingDoubleKeyFrame(-9, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(500)), new QuadraticEase { EasingMode = EasingMode.EaseOut }));
            jump.KeyFrames.Add(new EasingDoubleKeyFrame(0, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(640)), new QuadraticEase { EasingMode = EasingMode.EaseIn }));
            hop.BeginAnimation(TranslateTransform.YProperty, jump);
        }
    }
}
