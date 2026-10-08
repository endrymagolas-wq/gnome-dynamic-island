using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Island.Windows;

public sealed record DacpEndpoint(IPAddress Address, int Port);
public sealed record DnsRecord(string Name, ushort Type, uint Ttl, string? Target, int Port, IPAddress? Address);

public static class DacpDiscovery
{
    // Legacy unicast mDNS queries avoid taking exclusive ownership of UDP 5353.
    // Only the active sender's DACP service is queried, and only LAN addresses are accepted.
    public static async Task<DacpEndpoint?> Find(string id)
    {
        var service = "iTunes_Ctrl_" + id + "._dacp._tcp.local";
        var adapters = NetworkInterface.GetAllNetworkInterfaces().Where(n => n.OperationalStatus == OperationalStatus.Up && n.NetworkInterfaceType != NetworkInterfaceType.Loopback);
        var tasks = adapters.SelectMany(n => n.GetIPProperties().GatewayAddresses.Any(g => g.Address.AddressFamily == AddressFamily.InterNetwork && !g.Address.Equals(IPAddress.Any))
            ? n.GetIPProperties().UnicastAddresses.Where(a => a.Address.AddressFamily == AddressFamily.InterNetwork).Select(a => Query(service, a.Address, a.IPv4Mask))
            : Array.Empty<Task<DacpEndpoint?>>()).ToArray();
        if (tasks.Length == 0) return null;
        var results = await Task.WhenAll(tasks);
        return results.FirstOrDefault(r => r != null);
    }
    private static async Task<DacpEndpoint?> Query(string service, IPAddress local, IPAddress mask)
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(2));
        try
        {
            using var udp = new UdpClient(new IPEndPoint(local, 0));
            udp.Client.SetSocketOption(SocketOptionLevel.IP, SocketOptionName.MulticastInterface, local.GetAddressBytes());
            var multicast = new IPEndPoint(IPAddress.Parse("224.0.0.251"), 5353);
            var records = new List<DnsRecord>(); string? target = null; int port = 0;
            await udp.SendAsync(BuildQuery(service, 33), multicast, timeout.Token);
            while (!timeout.IsCancellationRequested)
            {
                var answer = await udp.ReceiveAsync(timeout.Token);
                if (!SameSubnet(answer.RemoteEndPoint.Address, local, mask)) continue;
                records.AddRange(Parse(answer.Buffer));
                var srv = records.LastOrDefault(r => r.Type == 33 && r.Ttl > 0 && r.Name.Equals(service, StringComparison.OrdinalIgnoreCase) && r.Port > 0);
                if (srv == null || srv.Target == null) continue;
                if (target != srv.Target)
                {
                    target = srv.Target; port = srv.Port;
                    await udp.SendAsync(BuildQuery(target, 1), multicast, timeout.Token);
                }
                var address = records.LastOrDefault(r => r.Type == 1 && r.Ttl > 0 && r.Name.Equals(target, StringComparison.OrdinalIgnoreCase) && r.Address != null && SameSubnet(r.Address, local, mask))?.Address;
                if (address != null) return new(address, port);
            }
        }
        catch (Exception e) when (e is SocketException or OperationCanceledException or InvalidDataException or ArgumentException) { }
        return null;
    }
    public static bool SameSubnet(IPAddress address, IPAddress local, IPAddress mask)
    {
        if (address.AddressFamily != AddressFamily.InterNetwork || IPAddress.IsLoopback(address) || address.Equals(IPAddress.Any)) return false;
        byte[] a = address.GetAddressBytes(), b = local.GetAddressBytes(), m = mask.GetAddressBytes();
        return a.Length == 4 && b.Length == 4 && m.Length == 4 && Enumerable.Range(0, 4).All(i => (a[i] & m[i]) == (b[i] & m[i]));
    }
    public static byte[] BuildQuery(string name, ushort type)
    {
        using var packet = new MemoryStream();
        var header = new byte[12]; BinaryPrimitives.WriteUInt16BigEndian(header, (ushort)Random.Shared.Next(1, 65536)); header[5] = 1; packet.Write(header);
        foreach (string label in name.TrimEnd('.').Split('.'))
        {
            var bytes = Encoding.UTF8.GetBytes(label); if (bytes.Length is < 1 or > 63) throw new ArgumentException("Invalid DNS label");
            packet.WriteByte((byte)bytes.Length); packet.Write(bytes);
        }
        packet.WriteByte(0); var tail = new byte[4]; BinaryPrimitives.WriteUInt16BigEndian(tail, type); tail[3] = 1; packet.Write(tail);
        return packet.ToArray();
    }
    public static IReadOnlyList<DnsRecord> Parse(byte[] packet)
    {
        var results = new List<DnsRecord>(); if (packet.Length < 12 || packet.Length > 65535 || (packet[2] & 0x80) == 0) return results;
        try
        {
            int pos = 12; int questions = U16(packet, 4), count = U16(packet, 6) + U16(packet, 8) + U16(packet, 10);
            if (questions > 128 || count > 512) return results;
            for (int i = 0; i < questions; i++) { Name(packet, ref pos); pos += 4; Bounds(packet, pos, 0); }
            for (int i = 0; i < count; i++)
            {
                string name = Name(packet, ref pos); Bounds(packet, pos, 10);
                ushort type = U16(packet, pos); uint ttl = BinaryPrimitives.ReadUInt32BigEndian(packet.AsSpan(pos + 4, 4)); int length = U16(packet, pos + 8); pos += 10; Bounds(packet, pos, length);
                int end = pos + length, offset = pos; string? target = null; int port = 0; IPAddress? address = null;
                if (type == 33 && length >= 7) { port = U16(packet, pos + 4); offset += 6; target = Name(packet, ref offset); if (offset > end) throw new InvalidDataException(); }
                else if (type == 1 && length == 4) address = new IPAddress(packet.AsSpan(pos, 4));
                else if (type == 12) { target = Name(packet, ref offset); if (offset > end) throw new InvalidDataException(); }
                results.Add(new(name, type, ttl, target, port, address)); pos = end;
            }
        }
        catch (InvalidDataException) { return Array.Empty<DnsRecord>(); }
        return results;
    }
    private static ushort U16(byte[] packet, int pos) { Bounds(packet, pos, 2); return BinaryPrimitives.ReadUInt16BigEndian(packet.AsSpan(pos, 2)); }
    private static void Bounds(byte[] packet, int pos, int length) { if (pos < 0 || length < 0 || pos > packet.Length - length) throw new InvalidDataException("Truncated DNS packet"); }
    private static string Name(byte[] packet, ref int pos)
    {
        int cursor = pos, next = -1, hops = 0, length = 0; var labels = new List<string>();
        while (hops++ < 128)
        {
            Bounds(packet, cursor, 1); int size = packet[cursor++];
            if (size == 0) { pos = next >= 0 ? next : cursor; return string.Join('.', labels); }
            if ((size & 0xC0) == 0xC0)
            {
                Bounds(packet, cursor, 1); int target = ((size & 63) << 8) | packet[cursor++]; if (next < 0) next = cursor;
                cursor = target; continue;
            }
            if (size > 63 || (length += size + 1) > 255) throw new InvalidDataException("Invalid DNS name");
            Bounds(packet, cursor, size); labels.Add(Encoding.UTF8.GetString(packet, cursor, size)); cursor += size;
        }
        throw new InvalidDataException("Cyclic DNS compression");
    }
}
