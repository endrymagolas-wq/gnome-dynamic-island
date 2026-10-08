using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;

namespace Island.Windows;

// Use Explorer's real overflow: existing icons, badges and each app's native
// left/right-click behavior stay intact. Only the flyout position is changed.
public sealed class NativeTrayPopup : IDisposable
{
    private IntPtr flyout, taskbar;
    private long previousStyle;
    private uint previousColor, previousFlags;
    private byte previousAlpha;
    private bool leased;
    private int generation;
    private readonly List<string> trace=new();
    public bool Opening { get; private set; }
    private readonly string backup = Path.Combine(Preferences.Data,"tray-layer-state.txt");
    public bool IsOpen => flyout!=IntPtr.Zero && IsWindowVisible(flyout);
    public static object TaskbarAppearance()
    {
        var window=FindWindow("Shell_TrayWnd",null);
        bool attributes=GetLayeredWindowAttributes(window,out uint color,out byte alpha,out uint flags);
        return new { style=GetWindowLongPtr(window,-20).ToInt64(),attributes,color,alpha,flags,visible=IsWindowVisible(window),state=ShellNative.TaskbarState };
    }
    public object Status
    {
        get
        {
            GetWindowRect(flyout,out var rectangle);
            bool transparent=leased && GetLayeredWindowAttributes(taskbar,out _,out byte alpha,out uint flags) && (flags&2)!=0 && alpha==0;
            return new { open=IsOpen,handle=flyout.ToInt64(),rectangle=new {left=rectangle.Left,top=rectangle.Top,width=rectangle.Right-rectangle.Left,height=rectangle.Bottom-rectangle.Top},taskbarTransparent=transparent,trace=trace.ToArray() };
        }
    }
    public async Task<bool> Open(int centerX,int top,int screenLeft,int screenRight)
    {
        if(Opening)return false;
        if(IsOpen || leased)
        {
            // Escape lets Explorer reset its own expanded-chevron state. Merely
            // hiding the XAML host leaves keyboard focus on a hidden flyout.
            if(IsOpen && ShellNative.GetForegroundWindow()==flyout) { Key(0x1B);await Task.Delay(120); }
            Close();return true;
        }
        Opening=true;
        try {
        Close();int request=++generation;trace.Clear(); taskbar=FindWindow("Shell_TrayWnd",null);
        if(taskbar==IntPtr.Zero)return false;
        previousStyle=GetWindowLongPtr(taskbar,-20).ToInt64();previousColor=0;previousAlpha=255;previousFlags=2;
        if((previousStyle&0x80000)!=0 && GetLayeredWindowAttributes(taskbar,out uint color,out byte alpha,out uint flags))
            { previousColor=color;previousAlpha=alpha;previousFlags=flags; }
        Directory.CreateDirectory(Preferences.Data);
        File.WriteAllText(backup,$"{previousStyle}\n{previousColor}\n{previousAlpha}\n{previousFlags}\n");
        leased=true;
        SetWindowLongPtr(taskbar,-20,new IntPtr(previousStyle|0x80000));
        if(!SetLayeredWindowAttributes(taskbar,0,0,2)){Close();return false;}
        ShellNative.ShowTaskbar(true);
        await Task.Delay(140);
        if(request!=generation)return true;
        SetForegroundWindow(taskbar);
        trace.Add("Before Win+B: "+ClassName(ShellNative.GetForegroundWindow()));
        ShellNative.Shortcut(0x42); // Windows+B focuses the notification-area chevron.
        await Task.Delay(100);if(request!=generation)return true;trace.Add("After Win+B: "+ClassName(ShellNative.GetForegroundWindow()));Key(0x0D);
        for(int attempt=0;attempt<20;attempt++)
        {
            if(request!=generation)return true;
            flyout=FindOverflow();
            if(flyout!=IntPtr.Zero && IsWindowVisible(flyout))break;
            await Task.Delay(50);
        }
        trace.Add("After Enter: "+ClassName(ShellNative.GetForegroundWindow()));
        if(!IsOpen){EnumWindows((window,_)=> { string name=ClassName(window);if(name.Contains("Tray",StringComparison.OrdinalIgnoreCase)||name.Contains("Overflow",StringComparison.OrdinalIgnoreCase))trace.Add(name+" visible="+IsWindowVisible(window));return true; },IntPtr.Zero);Close();return false;}
        GetWindowRect(flyout,out var rect);
        int x=Math.Clamp(centerX-(rect.Right-rect.Left)/2,screenLeft+12,Math.Max(screenLeft+12,screenRight-(rect.Right-rect.Left)-12));
        SetWindowPos(flyout,new IntPtr(-1),x,top,0,0,0x11);
        return true;
        } catch { Close();throw; } finally { Opening=false; }
    }
    public void Refresh()
    {
        if(leased && !Opening && !IsOpen)RestoreTaskbar();
    }
    public void Close()
    {
        generation++;
        if(flyout!=IntPtr.Zero && IsWindowVisible(flyout))ShowWindow(flyout,0);
        flyout=IntPtr.Zero;RestoreTaskbar();
    }
    private void RestoreTaskbar()
    {
        if(!leased)return;leased=false;
        // Hide before restoring alpha, so opening/closing the tray never flashes the taskbar.
        if(taskbar!=IntPtr.Zero)ShowWindow(taskbar,0);
        if(taskbar!=IntPtr.Zero){SetWindowLongPtr(taskbar,-20,new IntPtr(previousStyle));if((previousStyle&0x80000)!=0)SetLayeredWindowAttributes(taskbar,previousColor,previousAlpha,previousFlags);}
        File.Delete(backup);taskbar=IntPtr.Zero;
    }
    private static IntPtr FindOverflow()
    {
        IntPtr result=IntPtr.Zero;
        EnumWindows((window,_)=>
        {
            if(!IsWindowVisible(window))return true;
            var name=new StringBuilder(128);GetClassName(window,name,name.Capacity);
            if(name.ToString() is "TopLevelWindowForOverflowXamlIsland" or "NotifyIconOverflowWindow") { result=window;return false; }
            return true;
        },IntPtr.Zero);
        return result;
    }
    private static void Key(byte key){keybd_event(key,0,0,UIntPtr.Zero);keybd_event(key,0,2,UIntPtr.Zero);}
    private static string ClassName(IntPtr window){var name=new StringBuilder(128);GetClassName(window,name,name.Capacity);return name.ToString();}
    public void Dispose()=>Close();
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] private static extern IntPtr FindWindow(string name,string? title);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] private static extern int GetClassName(IntPtr window,StringBuilder name,int count);
    private delegate bool EnumWindowCallback(IntPtr window,IntPtr argument);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowCallback callback,IntPtr argument);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr window,int command);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr window);
    [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr window,out DesktopService.Rect rectangle);
    [DllImport("user32.dll")] private static extern bool SetWindowPos(IntPtr window,IntPtr after,int x,int y,int width,int height,uint flags);
    [DllImport("user32.dll",EntryPoint="GetWindowLongPtrW")] private static extern IntPtr GetWindowLongPtr(IntPtr window,int index);
    [DllImport("user32.dll",EntryPoint="SetWindowLongPtrW")] private static extern IntPtr SetWindowLongPtr(IntPtr window,int index,IntPtr value);
    [DllImport("user32.dll")] private static extern bool GetLayeredWindowAttributes(IntPtr window,out uint color,out byte alpha,out uint flags);
    [DllImport("user32.dll")] private static extern bool SetLayeredWindowAttributes(IntPtr window,uint color,byte alpha,uint flags);
    [DllImport("user32.dll")] private static extern void keybd_event(byte key,byte scan,uint flags,UIntPtr extra);
}
