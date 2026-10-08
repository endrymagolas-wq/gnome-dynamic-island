using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Net.NetworkInformation;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Forms = System.Windows.Forms;

namespace Island.Windows;

// The Linux floating panel and dock are separate surfaces from the media popover.
public sealed class DesktopShell : IDisposable
{
    private readonly MainWindow island;
    private readonly Window panel, dock;
    private readonly Border panelSurface, dockSurface;
    private readonly StackPanel left = new() { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Left }, right = new() { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
    private readonly StackPanel apps = new() { Orientation = Orientation.Horizontal };
    private readonly TextBlock title = new() { MaxWidth = 280, TextTrimming = TextTrimming.CharacterEllipsis, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(8,0,0,0), FontSize=11 };
    private readonly TextBlock network = Glyph("\uE839");
    private readonly TextBlock trayArrow = Glyph("\uE70D");
    private readonly TextBlock date = new() { FontSize=11, VerticalAlignment=VerticalAlignment.Center }, language = new() { FontSize=10 }, volume = new() { FontSize=11 };
    private ShellPopup? popup;
    private readonly NativeTrayPopup nativeTray = new();
    private List<DockPin>? dockPins;
    private DockEntry[] dockEntries = Array.Empty<DockEntry>();
    private Task navigationTask=Task.CompletedTask;
    private IntPtr lastExternalWindow=ShellNative.GetForegroundWindow();
    private List<ShellApp> liveApps=new();
    private readonly Dictionary<string,Button> navigation=new();
    private readonly StackPanel topApps=new() { Orientation=Orientation.Horizontal };
    public string LastNavigation { get; private set; } = "";
    public int NavigationCount { get; private set; }
    private readonly EdgeIntent intent = new();
    private readonly DispatcherTimer poll = new() { Interval=TimeSpan.FromMilliseconds(50) };
    private readonly DispatcherTimer refresh = new() { Interval=TimeSpan.FromSeconds(2) };
    private bool shown, disposed, refreshBusy, inspecting;
    private bool dockShown, dockAnimating;
    private int dockVisibilityGeneration;
    private DateTimeOffset? previewUntil;
    private DateTimeOffset dockHover=DateTimeOffset.UtcNow.AddSeconds(3);
    private string appKey = "", topAppKey = "";
    private readonly int previousTaskbar;
    private readonly bool previousTaskbarVisible;
    private DateTimeOffset nativeTrayUntil;
    private readonly string backup = Path.Combine(Preferences.Data,"taskbar-state.txt");
    public object Status => new { lastNavigation=LastNavigation, navigationCount=NavigationCount, popup=nativeTray.IsOpen?"tray":popup?.IsVisible==true?popup.Kind:null, nativeTray=nativeTray.Status, dockApps=dockEntries.Select(a=>a.Name).ToArray(), dockPins=dockPins?.Select(p=>p.Name).ToArray(), dockEntries=dockEntries.Select(e=>new {id=e.Id,name=e.Name,pinned=e.Pin!=null,running=e.Running,windowCount=e.Windows.Length,hasIcon=e.Icon!=null}).ToArray(), topApps=liveApps.Where(a=>a.TopBarOnly).Select(a=>a.Name).Distinct().ToArray(), revealed=shown, panelWidth=panelSurface.ActualWidth, panelHeight=panel.ActualHeight, clockOpacity=island.Opacity, taskbarVisible=ShellNative.TaskbarVisible, originalTaskbarVisible=previousTaskbarVisible, dockVisible=dock.IsVisible, dockWidth=dock.ActualWidth, appCount=AppCount, taskbarState=ShellNative.TaskbarState, originalTaskbarState=previousTaskbar };
    public int AppCount { get; private set; }
    public async Task<object> AuditTransition()
    {
        previewUntil=null; island.Collapse(); Reveal(false); await Task.Delay(350);
        var frames=new List<TransitionFrame>();
        EventHandler sample=(_,_)=>frames.Add(new(panel.Width,panel.Left,island.Opacity,island.Left,island.Top));
        CompositionTarget.Rendering+=sample;
        try { Preview(); await Task.Delay(550); previewUntil=null; Reveal(false); await Task.Delay(350); }
        finally { CompositionTarget.Rendering-=sample; }
        bool stableWindow=frames.Count>4 && frames.Max(f=>f.WindowWidth)-frames.Min(f=>f.WindowWidth)<.1 && frames.Max(f=>f.WindowLeft)-frames.Min(f=>f.WindowLeft)<.1;
        bool stableClock=frames.Count>4 && frames.All(f=>f.ClockOpacity==1) && frames.Max(f=>f.ClockLeft)-frames.Min(f=>f.ClockLeft)<.1 && frames.Max(f=>f.ClockTop)-frames.Min(f=>f.ClockTop)<.1;
        return new { stableWindow,stableClock,frames };
    }
    private record TransitionFrame(double WindowWidth,double WindowLeft,double ClockOpacity,double ClockLeft,double ClockTop);
    private static SolidColorBrush Brush(string value) => (SolidColorBrush)new BrushConverter().ConvertFromString(value)!;
    private static TextBlock Glyph(string value, int size=14) => new() { Text=value,FontFamily=new FontFamily("Segoe MDL2 Assets"),FontSize=size, VerticalAlignment=VerticalAlignment.Center };
    private static Button Button(object content, string tooltip, Action action) { var b = new Button { Content=content, ToolTip=tooltip, Padding=new Thickness(10,3,10,3), Focusable=false }; b.Click += (_,_)=>action(); return b; }
    private static Window Surface(string name, Border border) {
        var w = new Window { Title=name,WindowStyle=WindowStyle.None,AllowsTransparency=true,Background=Brushes.Transparent,ShowInTaskbar=false,ShowActivated=false,Topmost=true,ResizeMode=ResizeMode.NoResize,Content=border,UseLayoutRounding=true };
        w.SourceInitialized += (_,_)=> DesktopService.NoActivate(new WindowInteropHelper(w).Handle);
        return w;
    }
    public DesktopShell(MainWindow owner)
    {
        island=owner;
        panelSurface=new Border { Background=Brush("#000000"),BorderBrush=Brushes.Transparent,BorderThickness=new Thickness(0),CornerRadius=new CornerRadius(13),ClipToBounds=true,Width=128,HorizontalAlignment=HorizontalAlignment.Center };
        panel=Surface("Island · верхня панель",panelSurface);
        panel.SourceInitialized+=(_,_)=>ShellNative.ClickActivates(new WindowInteropHelper(panel).Handle);
        panel.Width=Screen.Bounds.Width*Scale-32; panel.Height=26; panel.Left=Screen.Bounds.Left*Scale+16; panel.Top=island.Top;
        var grid = new Grid { Width=panel.Width-12, HorizontalAlignment=HorizontalAlignment.Center }; panelSurface.Child=grid;
        left.Children.Add(Nav("apps",new Image { Source=new BitmapImage(new Uri("pack://application:,,,/Assets/owl.png")),Width=19,Height=19 },"Програми",()=>OpenNavigation("apps")));
        left.Children.Add(Nav("search",Glyph("\uE71E"),"Знайти вікно",()=>OpenNavigation("search")));
        left.Children.Add(title); grid.Children.Add(left);
        right.Children.Add(topApps);
        right.Children.Add(Nav("tray",trayArrow,"Фонові програми",()=>navigationTask=ToggleTray()));
        right.Children.Add(Nav("calendar",date,"Календар",()=>OpenNavigation("calendar")));
        right.Children.Add(Nav("language",language,"Мова клавіатури",()=>OpenNavigation("language")));
        right.Children.Add(Nav("network",network,"Мережа",()=>OpenNavigation("network")));
        right.Children.Add(Nav("volume",volume,"Медіа та звук",()=> { Dismiss();island.ShowMedia();island.Expand(); }));
        right.Children.Add(Nav("notifications",Glyph("\uE91C"),"Центр сповіщень Windows",async()=> { Dismiss();nativeTrayUntil=DateTimeOffset.UtcNow.AddSeconds(12);ShellNative.ShowTaskbar(true);await Task.Delay(160);ShellNative.Shortcut(0x4E); }));
        right.Children.Add(Nav("settings",Glyph("\uE713"),"Налаштування острівця",()=> { Dismiss();island.ShowDesktop();island.Expand(); }));
        grid.Children.Add(right);
        dockSurface = new Border { Background=Brush("#D91C1C1E"),BorderBrush=Brush("#30FFFFFF"),BorderThickness=new Thickness(1),CornerRadius=new CornerRadius(22),Padding=new Thickness(8,4,8,4),Child=apps };
        dock=Surface("Island · dock",dockSurface); dock.Height=58; dock.SizeToContent=SizeToContent.Width;
        dock.Opacity=0; dock.Show(); dock.Owner=owner;
        DockStyle.Apply(dock,dockSurface,apps);
        SetDockVisible(true);
        // Save before changing Explorer. Also recover the original after an interrupted run.
        Directory.CreateDirectory(Preferences.Data);
        previousTaskbar = File.Exists(backup) && int.TryParse(File.ReadAllText(backup),out int saved) ? saved : ShellNative.TaskbarState;
        var visibilityFile=Path.Combine(Preferences.Data,"taskbar-visible.txt");
        previousTaskbarVisible=File.Exists(visibilityFile) ? File.ReadAllText(visibilityFile)=="1" : ShellNative.TaskbarVisible;
        File.WriteAllText(visibilityFile,previousTaskbarVisible?"1":"0");
        File.WriteAllText(backup,previousTaskbar.ToString()); File.WriteAllText(Path.Combine(Preferences.Data,"taskbar-owner.txt"),Environment.ProcessId.ToString()); ShellNative.SetTaskbar(previousTaskbar | 1); ShellNative.ShowTaskbar(false);
        poll.Tick += (_,_)=> { var perf=UiPerf.Start(); Poll(); UiPerf.Report("shell.poll",perf); }; refresh.Tick += (_,_)=>Refresh();
        Refresh(); poll.Start(); refresh.Start();
    }
    private Button Nav(string id,object content,string tooltip,Action action)
    {
        var button=Button(content,tooltip,()=>{ LastNavigation=id;NavigationCount++;action(); });button.Tag=id;navigation[id]=button;return button;
    }
    private void OpenNavigation(string kind)
    {
        nativeTray.Close();
        if(popup?.IsVisible==true && popup.Kind==kind){popup.Close();popup=null;return;}
        popup?.Close(); popup=new ShellPopup(kind,liveApps,lastExternalWindow) { Owner=panel };
        if(inspecting) { popup.ShowInTaskbar=true;popup.SourceInitialized+=(_,_)=>ShellNative.Inspectable(new WindowInteropHelper(popup).Handle,true); }
        popup.Left=kind is "apps" or "search"?panel.Left:panel.Left+panel.Width-popup.Width;
        popup.Top=island.Top+36;popup.Show();popup.Activate();
    }
    private async Task ToggleTray()
    {
        if(nativeTray.Opening)return;
        try {
        popup?.Close();popup=null; island.Collapse();
        Preview();panel.UpdateLayout();
        var point=navigation["tray"].PointToScreen(new Point(navigation["tray"].ActualWidth/2,0));
        var screen=Screen.Bounds;
        if(!await nativeTray.Open((int)point.X,(int)((panel.Top+36)/Scale),screen.Left,screen.Right))
            Log.Error("background tray",new InvalidOperationException("Windows notification overflow did not open"));
        } catch(Exception error) { nativeTray.Close();Log.Error("background tray",error); }
    }
    private void Dismiss() { nativeTray.Close();popup?.Close();popup=null;previewUntil=null;Reveal(false); }
    public async Task InvokeNavigation(string id) { if(!navigation.TryGetValue(id,out var b)) throw new ArgumentException("Unknown navigation"); b.RaiseEvent(new RoutedEventArgs(System.Windows.Controls.Button.ClickEvent));await navigationTask; }
    public void PopupSnapshot(string path) { if(popup?.IsVisible!=true)throw new InvalidOperationException("No popup");popup.Snapshot(path); }
    public void Inspect(bool enabled)
    {
        inspecting=enabled;if(enabled){Preview();panel.ShowInTaskbar=true;dock.ShowInTaskbar=true;SetDockVisible(true);}else {panel.ShowInTaskbar=false;dock.ShowInTaskbar=false;}
        ShellNative.Inspectable(new WindowInteropHelper(panel).Handle,enabled);ShellNative.Inspectable(new WindowInteropHelper(dock).Handle,enabled);
    }
    public object NavigationGeometry() => navigation.Select(pair=> { var b=pair.Value;var point=b.PointToScreen(new Point(b.ActualWidth/2,b.ActualHeight/2));var local=b.TranslatePoint(new Point(b.ActualWidth/2,b.ActualHeight/2),panel);var hit=panel.InputHitTest(local) as DependencyObject;bool found=false;while(hit!=null){if(hit==b){found=true;break;}hit=VisualTreeHelper.GetParent(hit);}return new {id=pair.Key,x=point.X,y=point.Y,hit=found};}).ToArray();
    private Forms.Screen Screen { get { var all=Forms.Screen.AllScreens; return island.Settings.Monitor>=0 && island.Settings.Monitor<all.Length ? all[island.Settings.Monitor] : Forms.Screen.PrimaryScreen!; } }
    private double Scale => PresentationSource.FromVisual(island)?.CompositionTarget?.TransformFromDevice.M11 ?? 1;
    private void Poll()
    {
        if (disposed) return;
        nativeTray.Refresh();
        trayArrow.Text=nativeTray.IsOpen?"\uE70E":"\uE70D";
        if (DateTimeOffset.UtcNow>=nativeTrayUntil && !nativeTray.IsOpen && !nativeTray.Opening && ShellNative.TaskbarVisible) ShellNative.ShowTaskbar(false);
        var screen=Screen; var bounds=screen.Bounds; double scale=Scale;
        bool blocked=(!island.IsVisible && !inspecting) || island.IsExpanded;
        ShellNative.GetCursorPos(out var p);
        bool dragging=(ShellNative.GetAsyncKeyState(1)&0x8000)!=0 || (ShellNative.GetAsyncKeyState(2)&0x8000)!=0;
        bool edge=p.X>bounds.Left+16 && p.X<bounds.Right-16 && p.Y>=bounds.Top && p.Y<=bounds.Top+3;
        bool inside=p.X>=bounds.Left+16 && p.X<=bounds.Right-16 && p.Y>=bounds.Top && p.Y<bounds.Top+40/scale;
        bool show=intent.Update(edge,inside,blocked||dragging&&!shown,DateTimeOffset.UtcNow);
        if(popup?.IsVisible==true && !blocked) show=true;
        if(nativeTray.IsOpen && !blocked) show=true;
        if ((inspecting || previewUntil>DateTimeOffset.UtcNow) && !blocked) show=true;
        if (show!=shown) Reveal(show);
        // Like macOS autohide: reveal only when the pointer reaches the very bottom edge under the dock; once it is
        // shown, keep it while the pointer stays over it (so aiming at a chat box just above never pops it up).
        bool underDock=p.X>dock.Left/scale+40/scale && p.X<(dock.Left+dock.ActualWidth)/scale-40/scale;
        bool nearDock=underDock && p.Y<=bounds.Bottom && (p.Y>=bounds.Bottom-2 || dock.IsVisible && p.Y>bounds.Bottom-90/scale);
        if (nearDock || dock.IsMouseOver) dockHover=DateTimeOffset.UtcNow;
        var foreground=ShellNative.GetForegroundWindow(); ShellNative.GetWindowRect(foreground,out var rect);
        if(foreground!=IntPtr.Zero && !ShellNative.Owns(foreground)) lastExternalWindow=foreground;
        bool overlaps=!ShellNative.IsDesktopSurface(foreground) && rect.Bottom>(bounds.Bottom-80/scale) && rect.Right>dock.Left/scale && rect.Left<(dock.Left+dock.ActualWidth)/scale;
        bool menuOpen=apps.Children.OfType<Button>().Any(b=>b.ContextMenu?.IsOpen==true);
        bool dockVisible=inspecting || island.IsVisible && (!overlaps || nearDock || menuOpen || (DateTimeOffset.UtcNow-dockHover).TotalMilliseconds<600);
        SetDockVisible(dockVisible);
        // Floating Linux dock sits above the bottom edge, clear of Explorer's recovery strip.
        dock.Left=(bounds.Left+bounds.Width/2.0)*scale-dock.ActualWidth/2;
        dock.Top=bounds.Bottom*scale-dock.Height-12+DockStyle.BottomBleed; // the slab keeps its 12 px gap; the window reaches the edge for the shadow
        if (!shown && !panel.IsVisible) { panel.Left=bounds.Left*scale+16; panel.Top=island.Top; panel.Width=bounds.Width*scale-32; ((Grid)panelSurface.Child).Width=panel.Width-12; }
    }
    private void SetDockVisible(bool visible)
    {
        bool animate = island.Settings.Animations;
        if (visible == dockShown && (animate || !dockAnimating)) return;
        dockShown = visible;
        int generation = ++dockVisibilityGeneration;
        double from = dock.IsVisible ? dock.Opacity : 0;
        dock.BeginAnimation(UIElement.OpacityProperty, null);
        dockAnimating = false;
        if (!animate) {
            if (visible) dock.Show(); else dock.Hide();
            dock.Opacity = 1; dock.IsHitTestVisible = true;
            return;
        }
        if (visible) { dock.Opacity = from; dock.Show(); }
        dock.IsHitTestVisible = visible;
        dock.Opacity = visible ? 1 : 0;
        dockAnimating = true;
        var fade = new DoubleAnimation(from, visible ? 1 : 0, TimeSpan.FromMilliseconds(visible ? 140 : 100)) {
            EasingFunction = new QuadraticEase { EasingMode = visible ? EasingMode.EaseOut : EasingMode.EaseIn },
            FillBehavior = FillBehavior.Stop
        };
        fade.Completed += (_, _) => {
            if (disposed || generation != dockVisibilityGeneration) return;
            dockAnimating = false;
            if (!dockShown) dock.Hide();
            dock.BeginAnimation(UIElement.OpacityProperty, null);
            dock.Opacity = 1; dock.IsHitTestVisible = true;
        };
        dock.BeginAnimation(UIElement.OpacityProperty, fade);
    }
    public void Preview() { previewUntil=DateTimeOffset.UtcNow.AddSeconds(8); island.Collapse(); Reveal(true); }
    private void Reveal(bool value)
    {
        shown=value;
        if (value) {
            panel.Top=island.Top;
            left.Opacity=right.Opacity=0;
            panel.Show();
            // Keep the original clock above the expanding background, with no opacity swap.
            island.Surface.BorderBrush=Brushes.Transparent;
            ShellNative.Raise(new WindowInteropHelper(island).Handle);
        }
        int ms=island.Settings.Animations ? value?400:260 : 0;
        var easing=new CubicEase { EasingMode=EasingMode.EaseOut };
        var animation=new DoubleAnimation(panelSurface.ActualWidth>0?panelSurface.ActualWidth:128,value?panel.Width:128,TimeSpan.FromMilliseconds(ms)){ EasingFunction=easing };
        if (!value) animation.Completed+=(_,_)=> { if (!shown) { panel.Hide(); island.Surface.BorderBrush=Brush("#28FFFFFF"); } };
        panelSurface.BeginAnimation(FrameworkElement.WidthProperty,animation);
        foreach(var side in new[] { left,right }) side.BeginAnimation(UIElement.OpacityProperty,new DoubleAnimation(side.Opacity,value?1:0,TimeSpan.FromMilliseconds(value?180:60)){BeginTime=TimeSpan.FromMilliseconds(value?190:0)});
        if (!value && island.IsExpanded) { panel.Hide(); island.Surface.BorderBrush=Brush("#28FFFFFF"); }
    }
    private async void Refresh()
    {
        if(refreshBusy || disposed) return; refreshBusy=true;
        try {
        if(dockPins==null) dockPins=await Task.Run(DockCatalog.Load);
        // Window enumeration, the network check and the dock merge all run off the UI thread (they stalled animations).
        var pins=dockPins;
        var (open,online,merged)=await Task.Run(()=>{ var o=ShellNative.Apps(); return (o,NetworkInterface.GetIsNetworkAvailable(),DockCatalog.Merge(pins,o)); });
        if(disposed)return; liveApps=open; var perf=UiPerf.Start();
        date.Text=DateTime.Now.ToString("d MMM",System.Globalization.CultureInfo.GetCultureInfo("uk-UA"));
        language.Text=ShellNative.Language; var audio=island.Audio.Read(); volume.Text=$"♫  {audio.Volume*100:0}%";
        network.Text=online?"\uE839":"\uE871";
        var active=ShellNative.GetForegroundWindow(); title.Text=open.FirstOrDefault(a=>a.Handle==active)?.Name ?? "Робочий стіл";
        // Stable ordering prevents the dock moving underneath the pointer on focus changes.
        dockEntries=merged;
        string key=string.Join("|",dockEntries.Select(e=>e.Id+":"+string.Join(",",e.Windows.Select(a=>a.Handle.ToInt64()))));
        string newTopKey=string.Join("|",open.Where(a=>a.TopBarOnly).Select(a=>a.Path+":"+a.Handle));
        if(newTopKey!=topAppKey) { topAppKey=newTopKey;
            topApps.Children.Clear();
            foreach(var app in open.Where(a=>a.TopBarOnly).GroupBy(a=>a.Path).Select(g=>g.First())) {
                var shortcut=Button(new Image { Source=app.Icon,Width=17,Height=17 },"ChatGPT Classic",()=>{Dismiss();ShellNative.Switch(app.Handle);});topApps.Children.Add(shortcut);
            }
        }
        UiPerf.Report("shell.refresh(ui part)",perf);
        if(key==appKey) return; appKey=key; AppCount=dockEntries.Length;
        apps.Children.Clear();
        AddDock(Glyph("\uE80F",23),"Програми",Launchpad.Toggle,false);
        foreach(var entry in dockEntries.Take(24)) {
            var entries=entry.Windows;
            UIElement visual=entry.Icon != null ? entry.Name=="Codex" && dockSurface.Background is SolidColorBrush dockBackground && dockBackground.Color.R+dockBackground.Color.G+dockBackground.Color.B>384
                ? new Border { Width=30,Height=30,Background=Brush("#F2F2F7"),OpacityMask=new ImageBrush(entry.Icon) { Stretch=Stretch.Uniform } }
                : new Image { Source=entry.Icon,Width=30,Height=30 } : Glyph("\uE737",26);
            var button=AddDock(visual,entry.Name,()=> { if(entries.Length>0)ShellNative.Switch(entries[0].Handle);else if(entry.Pin!=null)DockCatalog.Launch(entry.Pin); },entry.Running);
            button.Tag=entry.Id;
            var menu=new ContextMenu();
            if(entry.Pin!=null) { var launch=new MenuItem { Header="Відкрити "+entry.Name }; launch.Click+=(_,_)=>DockCatalog.Launch(entry.Pin);menu.Items.Add(launch); }
            foreach(var app in entries) { var item=new MenuItem { Header=app.Title }; var handle=app.Handle; item.Click+=(_,_)=>ShellNative.Switch(handle); menu.Items.Add(item); }
            button.ContextMenu=menu;
        }
        AddDock(Glyph("\uE713",24),"Керування ПК",()=> { island.Expand(); island.ShowDesktop(); },false);
        } catch(Exception error) { Log.Error("desktop shell refresh",error); } finally { refreshBusy=false; }
    }
    private Button AddDock(UIElement icon,string tooltip,Action click,bool running)
    {
        var content=new Grid { Width=38,Height=45 }; content.Children.Add(icon);
        if(icon is FrameworkElement element) { element.VerticalAlignment=VerticalAlignment.Center; element.Margin=new Thickness(0,0,0,5); }
        if(icon is TextBlock glyph) glyph.Foreground=Brush("#F2F2F7");
        if(running) content.Children.Add(new Border { Width=4,Height=4,CornerRadius=new CornerRadius(2),Background=Brush("#CCFFFFFF"),VerticalAlignment=VerticalAlignment.Bottom,Margin=new Thickness(0,0,0,1) });
        var b=Button(content,tooltip,click); b.Padding=new Thickness(2,0,2,0);
        DockStyle.ConfigureButton(b,()=>island.Settings.Animations);
        apps.Children.Add(b); return b;
    }
    private void Zoom(ScaleTransform zoom,double target) { int ms=island.Settings.Animations?340:0; var spring=new SpringEase { Damping=.55 }; zoom.BeginAnimation(ScaleTransform.ScaleXProperty,new DoubleAnimation(target,TimeSpan.FromMilliseconds(ms)){EasingFunction=spring}); zoom.BeginAnimation(ScaleTransform.ScaleYProperty,new DoubleAnimation(target,TimeSpan.FromMilliseconds(ms)){EasingFunction=spring}); }
    public void Snapshot(string path,bool bottom)
    {
        var window=bottom?dock:panel; var surface=bottom?dockSurface:panelSurface; window.UpdateLayout(); double dpi=VisualTreeHelper.GetDpi(window).DpiScaleX;
        var bitmap=new RenderTargetBitmap((int)Math.Ceiling(window.ActualWidth*dpi),(int)Math.Ceiling(window.ActualHeight*dpi),96*dpi,96*dpi,PixelFormats.Pbgra32); bitmap.Render(surface);
        var encoder=new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap)); Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!); using var file=File.Create(path); encoder.Save(file);
    }
    public void Dispose() { if(disposed)return; disposed=true; poll.Stop();refresh.Stop();nativeTray.Dispose();popup?.Close();panel.Close();dock.Close();island.Surface.BorderBrush=Brush("#28FFFFFF");ShellNative.SetTaskbar(previousTaskbar);ShellNative.ShowTaskbar(previousTaskbarVisible);var visibilityFile=Path.Combine(Preferences.Data,"taskbar-visible.txt");if(File.Exists(visibilityFile))File.Delete(visibilityFile);if(File.Exists(backup))File.Delete(backup);var owner=Path.Combine(Preferences.Data,"taskbar-owner.txt");if(File.Exists(owner))File.Delete(owner); }
}
