using System;
using System.IO;
using System.Text.Json;

namespace Island.Windows;

public sealed class Preferences
{
    public bool Animations { get; set; } = true;
    public bool HideFullscreen { get; set; } = true;
    public bool HoverExpand { get; set; } = false;
    public bool AudioReactive { get; set; } = false;
    public bool EcoBrowsers { get; set; } = true;
    public bool AirPlayEnabled { get; set; } = true;
    public bool AirPlayRequirePin { get; set; } = true;
    public bool AirPlayVideoFullscreen { get; set; } = false;
    public bool AirPlayVideoKeepAspect { get; set; } = true;
    public int AirPlayVideoBufferSeconds { get; set; } = 5;
    public int Monitor { get; set; } = -1;
    public double Offset { get; set; } = 8;
    public DateTimeOffset? FocusUntil { get; set; }
    public static readonly string Data = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "IslandDesktopWindows");
    public static readonly string FileName = Path.Combine(Data, "preferences.json");
    public static Preferences Load()
    {
        try { return JsonSerializer.Deserialize<Preferences>(File.ReadAllText(FileName)) ?? new(); }
        catch { return new(); }
    }
    public void Save()
    {
        Directory.CreateDirectory(Data);
        var temporary = FileName + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true }));
        File.Move(temporary, FileName, true);
    }
}

// Island dimensions and timing in Windows device-independent pixels, tuned against the macOS Dynamic Island.
public static class IslandModel
{
    public const double CompactWidth = 128, CompactHeight = 26, CompactRadius = 13, ExpandedWidth = 680, ExpandedRadius = 34;
    // Fixed transparent stage hosting the morphing shape, with headroom for the spring overshoot and the soft shadow.
    public const double StageWidth = ExpandedWidth + 56, StageHeight = 340;
    public const int OpenMs = 480, CloseMs = 280, CloseDelayMs = 50, ContentDelayMs = 110, ContentFadeMs = 220, ContentOutMs = 90;
    public const double OpenDamping = .74, CloseDamping = .96;
    /// <summary>
    /// Rounded rectangle with Apple-style continuous corners: each corner curve starts ~1.45r along the edge and keeps
    /// the same visual depth as a circular arc of radius r, so the edge eases into the bend instead of snapping.
    /// Small shapes (the compact pill) fall back to a plain capsule.
    /// </summary>
    public static System.Windows.Media.Geometry Squircle(double width, double height, double radius)
    {
        double half = Math.Min(width, height) / 2; radius = Math.Clamp(radius, 0, half);
        double span = Math.Min(radius * 1.45, half);
        double pull = span <= 0 ? 0 : Math.Clamp((2.273 * radius / span - 1) / 3, .18, .4477) * span;
        var geometry = new System.Windows.Media.StreamGeometry();
        using (var c = geometry.Open())
        {
            c.BeginFigure(new System.Windows.Point(span, 0), true, true);
            c.LineTo(new(width - span, 0), true, false);
            c.BezierTo(new(width - pull, 0), new(width, pull), new(width, span), true, false);
            c.LineTo(new(width, height - span), true, false);
            c.BezierTo(new(width, height - pull), new(width - pull, height), new(width - span, height), true, false);
            c.LineTo(new(span, height), true, false);
            c.BezierTo(new(pull, height), new(0, height - pull), new(0, height - span), true, false);
            c.LineTo(new(0, span), true, false);
            c.BezierTo(new(0, pull), new(pull, 0), new(span, 0), true, false);
        }
        geometry.Freeze();
        return geometry;
    }
    /// <summary>Damped spring step response for progress t in [0, 1]; settles by t = 1, overshooting slightly when damping is below 1.</summary>
    public static double Spring(double t, double damping)
    {
        if (t <= 0) return 0;
        if (t >= 1) return 1;
        const double decay = 6.5;
        double omega = decay / damping, damped = omega * Math.Sqrt(Math.Max(1e-6, 1 - damping * damping));
        return 1 - Math.Exp(-decay * t) * (Math.Cos(damped * t) + decay / damped * Math.Sin(damped * t));
    }
    public static TimeSpan Remaining(DateTimeOffset? until, DateTimeOffset now) =>
        until.HasValue && until > now ? until.Value - now : TimeSpan.Zero;
    public static double Clamp(double value, double min, double max) => double.IsFinite(value) ? Math.Clamp(value, min, max) : min;
}

/// <summary>Spring step response as a WPF easing function (Damping below 1 overshoots and settles).</summary>
public sealed class SpringEase : System.Windows.Media.Animation.IEasingFunction
{
    public double Damping { get; init; } = .7;
    public double Ease(double normalizedTime) => IslandModel.Spring(normalizedTime, Damping);
}

/// <summary>Records UI-thread work that takes long enough to make animations stutter (diagnostics only).</summary>
public static class UiPerf
{
    public static long Start() => System.Diagnostics.Stopwatch.GetTimestamp();
    public static void Report(string label, long started)
    {
        double ms = (System.Diagnostics.Stopwatch.GetTimestamp() - started) * 1000.0 / System.Diagnostics.Stopwatch.Frequency;
        if (ms < 40) return;
        try { File.AppendAllText(Path.Combine(Preferences.Data, "ui-perf.log"), $"{DateTimeOffset.Now:HH:mm:ss.fff} {label} {ms:0}ms" + Environment.NewLine); } catch { }
    }
}

public static class Log
{
    public static void Error(string context, Exception exception)
    {
        try { Directory.CreateDirectory(Preferences.Data); File.AppendAllText(Path.Combine(Preferences.Data, "app.log"), $"{DateTimeOffset.Now:O} {context}: {exception.GetType().Name} HRESULT=0x{exception.HResult:X8} {exception.Message}\n{exception.StackTrace}\n"); } catch { }
    }
}
