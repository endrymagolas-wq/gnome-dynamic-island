using System;
using System.Collections.Generic;
using System.Linq;

namespace Island.Windows;

public static class DockTests
{
    public static object Run(out bool success)
    {
        var results = new List<(string Name,bool Passed)>();
        void Check(bool condition, string name) => results.Add((name,condition));
        var browser = new DockPin("Chrome", "Chrome", "chrome.lnk", @"C:\Apps\Chrome\chrome.exe", null);
        var first = new ShellApp(new IntPtr(1), "Chrome", browser.Target, null, "First");
        var second = first with { Handle = new IntPtr(2), Title = "Second" };
        var idle = DockCatalog.Merge(new[] { browser }, Array.Empty<ShellApp>());
        Check(idle.Length == 1 && !idle[0].Running && idle[0].Pin == browser, "Closed pinned apps remain available to launch");
        var grouped = DockCatalog.Merge(new[] { browser }, new[] { second, first });
        Check(grouped.Length == 1 && grouped[0].Windows.Length == 2 && grouped[0].Running, "Two windows of a pinned app produce one dock entry");
        var codex = new DockPin("OpenAI.Codex_pub!App", "Codex", "codex.lnk", "", null);
        var codexWindow = new ShellApp(new IntPtr(3), "Codex", @"C:\Program Files\WindowsApps\OpenAI.Codex_99_x64__pub\app\ChatGPT.exe", null, "Work", codex.Id);
        Check(DockCatalog.Merge(new[] { codex }, new[] { codexWindow }).Single().Running, "Packaged app identity groups independently of installed version");
        var classic = codexWindow with { Handle = new IntPtr(4), AppId = "OpenAI.ChatGPT-Desktop_pub!ChatGPT", Path = @"C:\Program Files\WindowsApps\OpenAI.ChatGPT-Desktop_1_x64__pub\ChatGPT.exe" };
        Check(DockCatalog.Merge(new[] { codex }, new[] { codexWindow, classic }).Single().Windows.Length == 1, "Classic ChatGPT remains separate from Codex and outside the dock");
        Check(DockCatalog.Merge(new[] { new DockPin(classic.AppId,"Classic","classic.lnk",classic.Path,null) }, new[] { classic }).Length == 0, "A Classic ChatGPT shortcut cannot create a second GPT dock entry");
        var pwa = first with { Handle = new IntPtr(5), Name = "YouTube", AppId = "Chrome._crx_video" };
        Check(DockCatalog.Merge(new[] { browser }, new[] { first, pwa }).Length == 2, "Chrome web apps remain distinct from the browser");
        var webPin = new DockPin(pwa.AppId,"YouTube","youtube.lnk",browser.Target,null);
        var webEntries = DockCatalog.Merge(new[] { browser, webPin }, new[] { first, pwa });
        Check(webEntries.Length == 2 && webEntries.All(e => e.Windows.Length == 1), "Pinned Chrome and web app each consume only their own window");
        var docker = new DockPin("Docker.DockerForWindows.Settings","Docker Desktop","docker.lnk",@"C:\Apps\Docker\Docker Desktop.exe",null);
        var dockerWindow = new ShellApp(new IntPtr(6),docker.Name,@"C:\Apps\Docker\frontend\Docker Desktop.exe",null,"Containers");
        Check(DockCatalog.Merge(new[] { docker },new[] { dockerWindow }).Length == 1, "Docker's frontend window groups with its installed launcher");
        Check(!docker.Matches(dockerWindow with { Path=@"C:\Other\Docker Desktop.exe" }), "An unrelated executable with the same filename never matches a pin");
        Check(DockCatalog.Merge(new[] { browser, browser with { Id="CHROME" } },new[] { first }).Length == 1, "Repeated shortcut identities cannot create duplicates");
        Check(DockCatalog.Merge(new[] { docker,browser },new[] { first,dockerWindow }).Select(e=>e.Id).SequenceEqual(new[] { docker.Id,browser.Id }), "Pinned order remains stable when windows arrive in another order");
        var unknown = first with { Handle=new IntPtr(7),Name="Other",Path=@"C:\Other\Other.exe",AppId="Other" };
        Check(DockCatalog.Merge(new[] { browser },new[] { unknown }).Length == 2, "Other running applications remain accessible after the pins");
        int passed=results.Count(value=>value.Passed);
        success=passed==results.Count;
        return new { passed,failed=results.Count-passed,tests=results.Select(value=>new { name=value.Name,passed=value.Passed }) };
    }
}
