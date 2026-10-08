using System;
using System.Windows;
using System.Windows.Media;

namespace Island.Windows;

// Matches Linux's playback-status indicator; real output-level response is opt-in.
public sealed class WaveBars : FrameworkElement
{
    public bool Playing { get; set; }
    public bool Animate { get; set; }
    public bool Reactive { get; set; }
    public double Level { get; set; }
    protected override void OnRender(DrawingContext context)
    {
        base.OnRender(context);
        var brush = new SolidColorBrush(Color.FromRgb(220, 229, 237)); brush.Freeze();
        double phase = Environment.TickCount64 / 250.0;
        for (int i = 0; i < 5; i++)
        {
            double value = Playing ? Animate ? .2 + .8 * Math.Abs(Math.Sin(phase + i * .8)) : .55 : .16;
            if (Reactive) value = Math.Max(.12, Level) * (.45 + .55 * Math.Abs(Math.Sin(phase * .7 + i)));
            double height = 2 + Math.Min(1, value) * 13;
            context.DrawRoundedRectangle(brush, null, new Rect(i * 4.0, (ActualHeight - height) / 2, 2, height), 1, 1);
        }
    }
}
