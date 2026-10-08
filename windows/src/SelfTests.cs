using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;

namespace Island.Windows;

public static class SelfTests
{
    public static object Run()
    {
        var results = new List<string>();
        void Check(bool condition, string name) { if (!condition) throw new InvalidOperationException(name); results.Add(name); }
        var now = DateTimeOffset.Parse("2026-10-05T20:00:00Z");
        Check(IslandModel.Remaining(null, now) == TimeSpan.Zero, "No focus timer");
        Check(IslandModel.Remaining(now.AddSeconds(-1), now) == TimeSpan.Zero, "Expired timer never negative");
        Check(IslandModel.Remaining(now.ToOffset(TimeSpan.FromHours(3)).AddMinutes(25), now) == TimeSpan.FromMinutes(25), "Timer respects absolute instant across time zones");
        Check(IslandModel.Clamp(double.NaN, 0, 1) == 0, "NaN volume rejected");
        Check(IslandModel.Clamp(2, 0, 1) == 1 && IslandModel.Clamp(-1, 0, 1) == 0, "Volume bounded");
        Check(MediaService.Friendly("com.spotify.client") == "Spotify", "Spotify session name");
        Check(MediaService.Friendly("chrome.exe") == "Chrome", "Chrome session name");
        var edge = new EdgeIntent();
        Check(!edge.Update(true,false,false,now), "Edge dwell starts without revealing");
        Check(!edge.Update(true,false,false,now.AddMilliseconds(299)), "Accidental edge contact remains hidden");
        Check(edge.Update(true,false,false,now.AddMilliseconds(300)), "Edge reveals after 300 ms");
        Check(edge.Update(false,true,false,now.AddSeconds(1)), "Panel remains while pointer is inside");
        Check(edge.Update(false,false,false,now.AddSeconds(2)), "Leaving starts the hide grace period");
        Check(edge.Update(false,false,false,now.AddMilliseconds(2599)), "Panel does not collapse early");
        Check(!edge.Update(false,false,false,now.AddMilliseconds(2600)), "Panel collapses after 600 ms outside");
        edge.Update(true,false,false,now.AddSeconds(3));
        Check(!edge.Update(true,false,true,now.AddSeconds(4)), "Dragging or fullscreen cancels edge intent");
        Check(!edge.Update(true,false,false,now.AddMilliseconds(4100)), "A blocked dwell cannot leak into the next reveal");
        Check(ShellNative.Apps().Count > 0, "Native window enumeration marshals and returns desktop applications");
        Check(new ShellApp(IntPtr.Zero,"ChatGPT Classic",@"C:\Program Files\WindowsApps\OpenAI.ChatGPT-Desktop_1.0_x64\ChatGPT.exe",null,"").TopBarOnly,"Classic ChatGPT belongs only in the top panel");
        Check(!new ShellApp(IntPtr.Zero,"Codex",@"C:\Program Files\WindowsApps\OpenAI.Codex_1.0_x64\Codex.exe",null,"").TopBarOnly,"Codex remains in the dock");
        Check(MediaService.Friendly(AirPlayService.SourceId) == "AirPlay", "AirPlay has a stable independent source identity");
        var wrapped = AirPlayService.Timeline(uint.MaxValue - 44099, 0, 44100);
        Check(wrapped.Position == 1 && wrapped.Duration == 2, "AirPlay RTP timeline survives the 32-bit counter wrapping");
        Check(AirPlayService.Timeline(0, 3 * 44100, 2 * 44100).Position == 2, "AirPlay progress remains within track duration");
        Check(AirPlayService.Timeline(0, 100, uint.MaxValue).Duration == 0, "Invalid AirPlay durations are discarded");
        var dns = DnsFixture(); var records = DacpDiscovery.Parse(dns);
        Check(records.Count == 2 && records[0].Target == "phone.local" && records[0].Port == 3689 && records[1].Address!.Equals(IPAddress.Parse("192.168.1.42")), "DACP DNS-SD reads compressed service and address records");
        Check(DacpDiscovery.Parse(dns[..^1]).Count == 0, "Truncated DNS responses cannot enable remote controls");
        var cycle = new byte[24]; cycle[2] = 128; cycle[7] = 1; cycle[12] = 192; cycle[13] = 12;
        Check(DacpDiscovery.Parse(cycle).Count == 0, "Cyclic DNS pointers cannot hang discovery");
        Check(DacpDiscovery.Parse(new byte[11]).Count == 0, "Short DNS headers are rejected");
        var local = IPAddress.Parse("192.168.1.17"); var mask = IPAddress.Parse("255.255.255.0");
        Check(DacpDiscovery.SameSubnet(IPAddress.Parse("192.168.1.42"),local,mask), "DACP accepts a sender in the local subnet");
        Check(!DacpDiscovery.SameSubnet(IPAddress.Parse("8.8.8.8"),local,mask) && !DacpDiscovery.SameSubnet(IPAddress.Loopback,local,mask), "DACP never forwards sender authorization to an external or loopback target");
        return new { passed = results.Count, failed = 0, tests = results };
    }
    private static byte[] DnsFixture()
    {
        var query = DacpDiscovery.BuildQuery("iTunes_Ctrl_ABCD._dacp._tcp.local",33); query[2] = 128; query[7] = 2;
        using var packet = new MemoryStream(); packet.Write(query);
        packet.Write(Convert.FromHexString("C00C00210001000000780013000000000E690570686F6E65056C6F63616C00"));
        packet.Write(Convert.FromHexString("0570686F6E65056C6F63616C0000010001000000780004C0A8012A"));
        return packet.ToArray();
    }
}
